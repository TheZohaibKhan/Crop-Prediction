from django.db import models
from django.contrib.auth.models import User

class Crop_Details(models.Model):
    farmer_id = models.BigAutoField(primary_key=True)
    farmer_name = models.CharField(max_length=100)
    contact_no = models.IntegerField()
    n = models.PositiveIntegerField()
    p = models.PositiveIntegerField()
    k = models.PositiveIntegerField()
    temperature = models.CharField(max_length=20)
    humidity = models.CharField(max_length=20)
    ph = models.CharField(max_length=20)
    rainfall = models.CharField(max_length=20)
    prediction = models.CharField(max_length=50)
    fertilizer = models.CharField(max_length=50)
    date = models.DateField()

    def __str__(self):
        return self.farmer_name

class fert_Details(models.Model):
    farmer_name = models.CharField(max_length=100)
    n = models.PositiveIntegerField()
    p = models.PositiveIntegerField()
    k = models.PositiveIntegerField()
    temperature = models.CharField(max_length=20)
    humidity = models.CharField(max_length=20)
    prediction = models.CharField(max_length=50)
    fertilizer = models.CharField(max_length=50)
    date = models.DateField()

    def __str__(self):
        return self.farmer_name

class images_data(models.Model):
    Images = models.FileField(upload_to='Images')

class image_data(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    Images = models.FileField(upload_to='crop_images/')
    quantity = models.PositiveIntegerField()
    crop_type = models.CharField(max_length=100, default='Other')
    price = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    location = models.CharField(max_length=200, blank=True, default='')
    notes = models.TextField(blank=True, default='')

    def __str__(self):
        return f"{self.crop_type} - {self.quantity} Kg by {self.user.username}"

class Vendor(models.Model):
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    phone_number = models.CharField(max_length=15)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)

    def __str__(self):
        return self.email

class Inquiry(models.Model):
    DIRECTION_CHOICES = [
        ('VF', 'Vendor to Farmer'),
        ('FV', 'Farmer to Vendor'),
    ]
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE)
    farmer = models.ForeignKey(User, on_delete=models.CASCADE)
    listing = models.ForeignKey(image_data, on_delete=models.CASCADE, null=True, blank=True)
    message = models.TextField()
    direction = models.CharField(max_length=2, choices=DIRECTION_CHOICES, default='VF')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        who = "Vendor" if self.direction == 'VF' else "Farmer"
        return f"{who} msg: {self.message[:30]}"

class PasswordResetOTP(models.Model):
    email = models.EmailField()
    otp = models.CharField(max_length=6)
    expiry_time = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.email} - {self.otp}"