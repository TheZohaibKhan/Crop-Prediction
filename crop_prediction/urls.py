from django.urls import path
from app import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.index, name='index'),
    path('services/', views.services, name='services'),
    path('blog/', views.blog, name='blog'),
    path('contact/', views.contact, name='contact'),
    path('about/', views.about, name='about'),
    path('forgot_password/', views.forgot_password, name='forgot_password'),

    path('register/', views.register, name='register'),
    path('log_in/', views.log_in, name='log_in'),
    path('log_out/', views.log_out, name='log_out'),

    path('dashboard/', views.dashboard, name='dashboard'),
    path('edit_profile/', views.edit_profile, name='edit_profile'),
    path('crop_report/', views.crop_report, name='crop_report'),
    path('fert_report/', views.fert_report, name='fert_report'),
    path('report/', views.report, name='report'),
    path('report1/', views.report1, name='report1'),

    path('crop_prediction/', views.crop_prediction, name='crop_prediction'),
    path('crop_dis/', views.crop_dis, name='crop_dis'),
    path('fert_rec/', views.fert_rec, name='fert_rec'),
    path('upload/', views.upload, name='upload'),
    path('predict/', views.predict, name='predict'),

    path('news/', views.news, name='news'),
    path('search_news/', views.search_news, name='search_news'),

    path('e_market/', views.e_market, name='e_market'),
    path('upload_crop_image/', views.upload_crop_image, name='upload_crop_image'),
    path('delete_listing/<int:item_id>/', views.delete_listing, name='delete_listing'),

    path('vendor_register/', views.vendor_register, name='vendor_register'),
    path('vendor_log_in/', views.vendor_log_in, name='vendor_log_in'),
    path('vendor_dashboard/', views.vendor_dashboard, name='vendor_dashboard'),
    path('vendor_edit_profile/', views.vendor_edit_profile, name='vendor_edit_profile'),
    path('add_to_cart/<int:item_id>/', views.add_to_cart, name='add_to_cart'),
    path('remove_from_cart/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),

    path('send_listing_inquiry/<int:listing_id>/', views.send_listing_inquiry, name='send_listing_inquiry'),
    path('send_cart_inquiry/', views.send_cart_inquiry, name='send_cart_inquiry'),
    path('delete_inquiry/<int:inquiry_id>/', views.delete_inquiry, name='delete_inquiry'),
    path('delete_vendor_inquiry/<int:inquiry_id>/', views.delete_vendor_inquiry, name='delete_vendor_inquiry'),
    path('reply_inquiry/<int:inquiry_id>/', views.reply_inquiry, name='reply_inquiry'),
    path('vendor_reply_inquiry/<int:inquiry_id>/', views.vendor_reply_inquiry, name='vendor_reply_inquiry'),

    path('send_reset_otp/', views.send_reset_otp, name='send_reset_otp'),
    path('verify_reset_otp/', views.verify_reset_otp, name='verify_reset_otp'),
    path('reset_password/', views.reset_password, name='reset_password'),

    path('loan1/', views.loan1, name='loan1'),
    path('insurance/', views.insurance, name='insurance'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)