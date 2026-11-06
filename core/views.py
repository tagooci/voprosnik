from django.shortcuts import redirect, render


def login(request):
    if request.method == "POST":
        response = redirect("questions:index")
        # Временная имитация входа для демонстрации страниц.
        response.set_cookie("demo_user", "1", httponly=True, samesite="Lax")
        return response
    return render(request, "core/login.html")


def logout(request):
    response = redirect("questions:index")
    response.delete_cookie("demo_user")
    return response


def signup(request):
    return render(request, "core/signup.html")


def profile(request):
    return render(request, "core/profile.html")
