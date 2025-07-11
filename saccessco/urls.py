"""
URL configuration for saccessco project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
# from django.contrib import admin
from django.urls import path

from saccessco.views import PageChangeAPIView, UserPromptAPIView, TestHtmlView, PageManipulatorTestPageView, \
    FormSubmitSuccessView

urlpatterns = [
    #    path('admin/', admin.site.urls),
    path('saccessco/user_prompt/', UserPromptAPIView.as_view(), name='user_prompt'),
    path('saccessco/page_change/', PageChangeAPIView.as_view(), name='page_change'),
    path('test-page/', TestHtmlView.as_view(), name='test_page'),
    path('test-page-manipulator/', PageManipulatorTestPageView.as_view(), name='test_page_manipulator'),
    path('form-submit-success/', FormSubmitSuccessView.as_view(), name='form_submit_success'),

]
