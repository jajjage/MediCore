from django.http import HttpResponse
from django.shortcuts import render


# Function-based view for the homepage
def home(request):
    return HttpResponse("Welcome to the Homepage!")


# Function-based view for an about page
def about(request):
    return HttpResponse("This is the About Page.")


# Function-based view for rendering a template
def contact(request):
    return render(request, "contact.html", {"title": "Contact Us"})
