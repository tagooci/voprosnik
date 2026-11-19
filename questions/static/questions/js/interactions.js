function errorMessage(data, status) {
    if (data.error) return data.error;
    if (data.errors) {
        return Object.values(data.errors).flat().map(error => error.message).join(' ');
    }
    if (status === 403) return 'Действие запрещено или CSRF-токен устарел. Обновите страницу.';
    if (status === 405) return 'Неверный метод запроса. Обновите страницу.';
    return 'Не удалось выполнить действие. Попробуйте ещё раз.';
}

async function sendForm(form, submitter) {
    const body = new FormData(form);
    if (submitter?.name) body.set(submitter.name, submitter.value);
    const response = await fetch(form.action, {
        method: 'POST',
        body,
        credentials: 'same-origin',
        headers: {'X-CSRFToken': body.get('csrfmiddlewaretoken'), 'X-Requested-With': 'XMLHttpRequest'},
    });
    const data = await response.json().catch(() => ({}));
    if (response.status === 401) {
        const login = new URL(data.login_url || '/login/', window.location.origin);
        login.searchParams.set('next', window.location.pathname + window.location.search);
        window.location.assign(login);
        return null;
    }
    if (!response.ok) throw new Error(errorMessage(data, response.status));
    return data;
}

document.addEventListener('submit', async event => {
    const form = event.target;
    if (!form.matches('[data-vote-form], [data-correct-form]')) return;
    event.preventDefault();
    if (form.dataset.pending) return;
    form.dataset.pending = 'true';
    const errorBox = form.querySelector('[data-ajax-error]');
    errorBox.textContent = '';
    const buttons = [...form.querySelectorAll('button')];
    const previousStates = buttons.map(button => button.disabled);
    buttons.forEach(button => { button.disabled = true; });
    let completed = false;
    try {
        const data = await sendForm(form, event.submitter);
        if (!data) return;
        if (form.matches('[data-vote-form]')) {
            form.querySelector('[data-rating]').textContent = data.rating;
            buttons.forEach(button => {
                button.disabled = Number(button.value) === data.value;
                button.title = button.disabled ? 'Вы уже поставили эту оценку' : 'Изменить оценку';
            });
        } else {
            document.querySelectorAll('[data-answer-id]').forEach(card => {
                const selected = Number(card.dataset.answerId) === data.answer_id;
                card.classList.toggle('border-success', selected);
                card.querySelector('[data-correct-badge]').hidden = !selected;
                const button = card.querySelector('[data-correct-form] button');
                if (button) {
                    button.disabled = selected;
                    button.textContent = selected ? 'Выбран правильным' : 'Выбрать правильным';
                }
            });
        }
        completed = true;
    } catch (error) {
        errorBox.textContent = error instanceof TypeError ? 'Нет соединения с сервером. Попробуйте ещё раз.' : error.message;
    } finally {
        if (!completed) buttons.forEach((button, index) => { button.disabled = previousStates[index]; });
        delete form.dataset.pending;
    }
});
