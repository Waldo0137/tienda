from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import BadHeaderError, send_mail
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
import json

from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from datetime import date, datetime
from inventory.models import *
from pickle import FALSE
from pos.models import *
from django.db.models import Count, Sum
    
from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import SetPasswordForm
from django.contrib import messages
from django.urls import reverse_lazy
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.shortcuts import render

User = get_user_model()

from.forms import *

def login_user(request):
    logout(request)
    resp = {"status":'failed','msg':''}
    username = ''
    password = ''
    if request.POST:
        username = request.POST['username']
        password = request.POST['password']

        user = authenticate(username=username, password=password)
        if user is not None:
            if user.is_active:
                login(request, user)
                resp['status']='success'
            else:
                resp['msg'] = "Incorrect username or password"
        else:
            resp['msg'] = "Incorrect username or password"
        return HttpResponse(json.dumps(resp),content_type='application/json')

    
def logoutuser(request):
    logout(request)
    return redirect('/')


@login_required
def home(request):
    now = datetime.now()
    current_year = now.strftime("%Y")
    current_month = now.strftime("%m")
    current_day = now.strftime("%d")
    categories = len(Category.objects.all())
    products = len(Products.objects.all())
    transaction = len(Sales.objects.filter(
        date_added__year=current_year,
        date_added__month = current_month,
        date_added__day = current_day
    ))
    today_sales = Sales.objects.filter(
        date_added__year=current_year,
        date_added__month = current_month,
        date_added__day = current_day
    ).all()
    total_sales = sum(today_sales.values_list('grand_total',flat=True))
    context = {
        'page_title':'Home',
        'categories' : categories,
        'products' : products,
        'transaction' : transaction,
        'total_sales' : total_sales,
    }
    return render(request, 'home.html',context)


def about(request):
    context = {
        'page_title':'About',
    }
    return render(request, 'about.html',context)



def register_user(request):
    if request.method == 'POST':
        resp = {"status": 'failed', 'msg': ''}
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()
        email = request.POST.get('email', '').strip()

        if username and password and confirm_password and email:
            if password != confirm_password:
                resp['msg'] = 'Passwords do not match'
            elif User.objects.filter(username=username).exists():
                resp['msg'] = 'Username already exists'
            elif User.objects.filter(email=email).exists():
                resp['msg'] = 'Email already exists'
            else:
                user = User.objects.create_user(username=username, password=password, email=email)
                user.save()
                resp['status'] = 'success'
        else:
            resp['msg'] = 'Please fill out all fields'
        
        return HttpResponse(json.dumps(resp), content_type='application/json')

    return render(request, 'core/register.html')



def password_reset_request(request):
    if request.method == 'POST':
        form = PasswordResetEmailForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            if '@' in email:
                associated_users = User.objects.filter(email=email)
                if associated_users.exists():
                    for user in associated_users:
                        subject = "Reset Your Password"
                        email_template_name = "core/password_reset_email.txt"
                        c = {
                            "email": email,
                            "uid": urlsafe_base64_encode(force_bytes(user.pk)),
                            "user": user,
                            'token': default_token_generator.make_token(user),
                        }
                        email_content = render_to_string(email_template_name, c)
                        
                        try:
                            
                            print("Simulated Email Content:")
                            print(email_content)
                            
                            
                            messages.success(request, 'Se ha enviado un correo con instrucciones para resetear tu contraseña.')
                            return redirect('password_reset_confirm', uidb64=c['uid'], token=c['token'])
                        except BadHeaderError:
                            messages.error(request, 'Hubo un problema al enviar el correo. Por favor, intenta nuevamente más tarde.')
                            return redirect('password_reset_request')
                else:
                    messages.error(request, 'No hay usuarios asociados a este correo electrónico.')
            else:
                messages.error(request, 'Por favor, introduce un correo electrónico válido.')  
        else:
            messages.error(request, 'Por favor, corrige los errores en el formulario.')
    else:
        form = PasswordResetEmailForm()
    return render(request=request, template_name="core/password_reset.html", context={"form": form})



def password_reset_confirm(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    
    if user is not None and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            form = SetPasswordForm(user, request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, 'Tu contraseña ha sido actualizada con éxito.')
                return redirect('login')  # Redirigir al login después de cambiar la contraseña
        else:
            form = SetPasswordForm(user)
        
        # Aquí pasamos el nombre de usuario y el correo electrónico como contexto al template
        context = {
            'form': form,
            'username': user.username,
            'email': user.email,
        }
        return render(request, 'core/password_reset_confirm.html', context)
    else:
        messages.error(request, 'El enlace de reseteo de contraseña es inválido o ha expirado.')
        return redirect('password_reset_request')  # Redirigir de nuevo a la solicitud de reseteo de contraseña

