from django.shortcuts import render, redirect, HttpResponse, get_object_or_404
from django.contrib import messages
from app.auth import authentication, input_verification, input_verification1
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_control
from app.models import *
import keras
from keras.models import load_model
from keras.preprocessing.image import img_to_array, load_img
from keras.applications.vgg19 import preprocess_input
import numpy as np
import tensorflow as tf
import pickle
from datetime import datetime
from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import random
from django.utils.timezone import now, timedelta
from django.utils.html import strip_tags
from django.contrib.auth.hashers import make_password, check_password

# ─── HELPER: user context for sidebar ──────────────────
def get_user_context(request):
    if request.user.is_authenticated:
        return {
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
        }
    return {}

# ─── STATIC / HOMEPAGE VIEWS ────────────────────────────
def index(request):
    return render(request, "index.html", {'navbar': 'home'})

def services(request):
    return render(request, 'services.html', {})

def blog(request):
    categories = [
        {'name': 'Crop Management', 'count': 28, 'cls': 'cat-g'},
        {'name': 'Soil Science', 'count': 19, 'cls': 'cat-g'},
        {'name': 'Government Schemes', 'count': 24, 'cls': 'cat-w'},
        {'name': 'Disease & Pests', 'count': 15, 'cls': 'cat-s'},
        {'name': 'AgriTech', 'count': 12, 'cls': 'cat-b'},
        {'name': 'Weather & Climate', 'count': 10, 'cls': 'cat-b'},
        {'name': 'Market Prices', 'count': 18, 'cls': 'cat-w'},
    ]
    tags = [
        'Kharif', 'Rabi', 'NPK', 'Soil pH', 'Monsoon', 'MSP',
        'PMFBY', 'Organic Farming', 'Drip Irrigation', 'Wheat',
        'Tomato', 'Onion', 'Disease', 'Fertilizer', 'PM-KISAN', 'Seed Treatment'
    ]
    return render(request, 'blog.html', {'categories': categories, 'tags': tags})

def contact(request):
    social_links = [
        {'icon': 'fab fa-facebook-f', 'label': 'Facebook', 'bg': 'rgba(66,103,178,.12)'},
        {'icon': 'fab fa-instagram', 'label': 'Instagram', 'bg': 'rgba(225,48,108,.1)'},
        {'icon': 'fab fa-youtube', 'label': 'YouTube', 'bg': 'rgba(255,0,0,.09)'},
        {'icon': 'fab fa-twitter', 'label': 'Twitter', 'bg': 'rgba(29,161,242,.1)'},
    ]
    return render(request, 'contact.html', {'social_links': social_links})

def forgot_password(request):
    return render(request, 'forgot_password.html', {})

def about(request):
    team_members = [
        {'name': 'Dr. Priya Sharma', 'role': 'Lead Agronomist', 'icon': 'fas fa-user-tie', 'desc': 'PhD in Agricultural Sciences, IIT Bombay. 12+ years in precision farming research.'},
        {'name': 'Rahul Patil', 'role': 'AI/ML Engineer', 'icon': 'fas fa-brain', 'desc': 'Specialist in computer vision and NLP for agricultural applications.'},
        {'name': 'Anjali Desai', 'role': 'Soil Scientist', 'icon': 'fas fa-flask', 'desc': 'Expert in soil nutrient analysis and fertilizer optimization for Indian crops.'},
        {'name': 'Vikram Nair', 'role': 'Full-Stack Developer', 'icon': 'fas fa-code', 'desc': 'Builds the platform infrastructure that serves thousands of farmers daily.'},
    ]
    stats = [
        {'value': '22+', 'label': 'Crops Supported'},
        {'value': '95%', 'label': 'Prediction Accuracy'},
        {'value': '38', 'label': 'Disease Classes'},
        {'value': '10K+', 'label': 'Farmers Helped'},
    ]
    return render(request, 'about.html', {'team_members': team_members, 'stats': stats})

# ─── AUTH ──────────────────────────────────────────────
def register(request):
    if request.method == "POST":
        first_name = request.POST['first_name']
        last_name = request.POST['last_name']
        phone_number = request.POST['phone_number']
        username = request.POST['username']
        password = request.POST['password']
        password1 = request.POST['password1']
        verify = authentication(first_name, last_name, password, password1, phone_number)
        if verify == "success":
            user = User.objects.create_user(username, password, password1)
            user.first_name = first_name
            user.last_name = last_name
            user.email = username
            user.save()
            messages.success(request, "Your Account has been Created.")
            return redirect("/")
        else:
            messages.error(request, verify)
            return redirect("register")
    return render(request, "register.html", {'navbar': 'register'})

def log_in(request):
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(username=username, password=password)
        if user is not None:
            login(request, user)
            request.session.pop('vendor_id', None)
            request.session['cart'] = []
            request.session.modified = True
            messages.success(request, "Log In Successful...!")
            return redirect("dashboard")
        else:
            messages.error(request, "Invalid User...!")
            return redirect("log_in")
    return render(request, "log_in.html", {'navbar': 'log_in'})

@login_required(login_url="log_in")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def log_out(request):
    request.session.pop('vendor_id', None)
    request.session['cart'] = []
    request.session.modified = True
    logout(request)
    messages.success(request, "Log out Successfuly...!")
    return redirect("/")

# ─── DASHBOARD & REPORTS ────────────────────────────────
@login_required(login_url="log_in")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def dashboard(request):
    inquiries = Inquiry.objects.filter(farmer=request.user).order_by('-created_at')
    context = {
        'first_name': request.user.first_name,
        'last_name': request.user.last_name,
        'inquiries': inquiries,
    }
    return render(request, "dashboard.html", context)

# ─── FARMER EDIT PROFILE ────────────────────────────────
@login_required(login_url="log_in")
def edit_profile(request):
    user = request.user
    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name  = request.POST.get('last_name', '').strip()
        old_pw     = request.POST.get('old_password', '')
        new_pw     = request.POST.get('new_password', '')

        if not first_name or not last_name:
            messages.error(request, "First and last name are required.")
            return redirect('edit_profile')

        user.first_name = first_name
        user.last_name  = last_name
        user.save()
        messages.success(request, "Profile updated.")

        if old_pw and new_pw:
            if user.check_password(old_pw):
                if len(new_pw) >= 8:
                    user.set_password(new_pw)
                    user.save()
                    messages.success(request, "Password changed. Please log in again.")
                    return redirect('log_out')
                else:
                    messages.error(request, "New password must be at least 8 characters.")
            else:
                messages.error(request, "Old password is incorrect.")
        return redirect('dashboard')
    return render(request, 'edit_profile.html', {'user': user})

@login_required(login_url="log_in")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def crop_report(request):
    crop_data = Crop_Details.objects.last()
    context = {
        'first_name': request.user.first_name,
        'last_name': request.user.last_name,
        'crop_data': crop_data
    }
    if request.method == "POST":
        return redirect("report")
    return render(request, "crop_report.html", context)

@login_required(login_url="log_in")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def fert_report(request):
    fert_data = fert_Details.objects.last()
    context = {
        'first_name': request.user.first_name,
        'last_name': request.user.last_name,
        'fert_data': fert_data
    }
    if request.method == "POST":
        return redirect("report1")
    return render(request, "fert_report.html", context)

@login_required(login_url="log_in")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def report(request):
    crop_data = Crop_Details.objects.last()
    ctx = get_user_context(request)
    ctx['crop_data'] = crop_data
    return render(request, "report.html", ctx)

@login_required(login_url="log_in")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def report1(request):
    fert_data = fert_Details.objects.last()
    ctx = get_user_context(request)
    ctx['fert_data'] = fert_data
    return render(request, "report1.html", ctx)

# ─── STATIC PAGES (now with user info) ──────────────────
def loan1(request):
    ctx = {'navbar': 'home'}
    ctx.update(get_user_context(request))
    return render(request, "loan1.html", ctx)

def insurance(request):
    ctx = {'navbar': 'home'}
    ctx.update(get_user_context(request))
    return render(request, "insurance.html", ctx)

# ─── CROP PREDICTION ────────────────────────────────────
def crop_prediction(request):
    if request.method == "POST":
        farmer_name = request.POST['farmer_name']
        contact_no = request.POST['contact_no']
        n = request.POST['n']
        p = request.POST['p']
        k = request.POST['k']
        temperature = request.POST['temperature']
        humidity = request.POST['humidity']
        ph = request.POST['ph']
        rainfall = request.POST['rainfall']
        verify = input_verification(farmer_name, contact_no, n, p, k, temperature, humidity, ph, rainfall)
        if verify == "Success":
            with open('dataset/crop_prediction.pkl', 'rb') as f:
                NaiveBayes = pickle.load(f)
            data = np.array([[n, p, k, temperature, humidity, ph, rainfall]], dtype=float)
            pred = NaiveBayes.predict(data)
            message = 'Predicted Crop is : ' + pred[0]
            crop = Crop_Details(farmer_name=farmer_name, contact_no=contact_no,
                                n=n, p=p, k=k, temperature=temperature,
                                humidity=humidity, ph=ph, rainfall=rainfall)
            crop.prediction = message
            crop.date = datetime.today()
            crop.save()
            messages.info(request, message)
            return redirect("crop_report")
        else:
            messages.error(request, verify)
            return redirect("dashboard")
    ctx = {'navbar': 'home'}
    ctx.update(get_user_context(request))
    return render(request, "crop_prediction.html", ctx)

def crop_dis(request):
    ctx = {'navbar': 'home'}
    ctx.update(get_user_context(request))
    return render(request, "crop_dis.html", ctx)

# ─── FERTILIZER RECOMMENDATION ──────────────────────────
def fert_rec(request):
    if request.method == "POST":
        farmer_name = request.POST['farmer_name']
        n = request.POST['n']
        p = request.POST['p']
        k = request.POST['k']
        temperature = request.POST['temperature']
        humidity = request.POST['humidity']
        verify = input_verification1(farmer_name, n, p, k, temperature, humidity)
        if verify == "Success":
            with open('dataset/Fertilizer_Classifier.pkl', 'rb') as f:
                NaiveBayes = pickle.load(f)
            data = np.array([[n, p, k, temperature, humidity]], dtype=float)
            pred = NaiveBayes.predict(data)
            message = 'Predicted Fertilizer is : ' + pred[0]
            fert = fert_Details(farmer_name=farmer_name, n=n, p=p, k=k,
                                temperature=temperature, humidity=humidity, fertilizer=pred)
            fert.prediction = message
            fert.date = datetime.today()
            fert.save()
            messages.info(request, message)
            return redirect("fert_report")
        else:
            messages.error(request, verify)
            return redirect("dashboard")
    ctx = {'navbar': 'home'}
    ctx.update(get_user_context(request))
    return render(request, "fert_rec.html", ctx)

# ─── DISEASE DETECTION ──────────────────────────────────
label_mapping = {
    0: 'Apple___Apple_scab',
    1: 'Apple___Black_rot',
    2: 'Apple___Cedar_apple_rust',
    3: 'Apple___healthy',
    4: 'Blueberry___healthy',
    5: 'Cherry_(including_sour)___Powdery_mildew',
    6: 'Cherry_(including_sour)___healthy',
    7: 'Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot',
    8: 'Corn_(maize)__Common_rust',
    9: 'Corn_(maize)___Northern_Leaf_Blight',
    10: 'Corn_(maize)___healthy',
    11: 'Grape___Black_rot',
    12: 'Grape__Esca(Black_Measles)',
    13: 'Grape__Leaf_blight(Isariopsis_Leaf_Spot)',
    14: 'Grape___healthy',
    15: 'Orange__Haunglongbing(Citrus_greening)',
    16: 'Peach___Bacterial_spot',
    17: 'Peach___healthy',
    18: 'Pepper,bell__Bacterial_spot',
    19: 'Pepper,bell__healthy',
    20: 'Potato___Early_blight',
    21: 'Potato___Late_blight',
    22: 'Potato___healthy',
    23: 'Raspberry___healthy',
    24: 'Soybean___healthy',
    25: 'Squash___Powdery_mildew',
    26: 'Strawberry___Leaf_scorch',
    27: 'Strawberry___healthy',
    28: 'Tomato___Bacterial_spot',
    29: 'Tomato___Early_blight',
    30: 'Tomato___Late_blight',
    31: 'Tomato___Leaf_Mold',
    32: 'Tomato___Septoria_leaf_spot',
    33: 'Tomato___Spider_mites Two-spotted_spider_mite',
    34: 'Tomato___Target_Spot',
    35: 'Tomato___Tomato_Yellow_Leaf_Curl_Virus',
    36: 'Tomato___Tomato_mosaic_virus',
    37: 'Tomato___healthy'
}

label_descriptions = {
    'Apple___Apple_scab': 'Apple scab is a fungal disease caused by Venturia inaequalis. It produces olive-green to brown velvety spots on leaves and fruit, leading to distortion, premature leaf drop, and cracked or corky fruit surfaces. It thrives in cool, wet spring weather.',
    'Apple___Black_rot': 'Black rot is caused by the fungus Botryosphaeria obtusa. It causes circular, brown lesions on leaves with purple margins and leads to mummified, black shrivelled fruit. Infected wood can develop cankers. The disease spreads rapidly in warm, humid conditions.',
    'Apple___Cedar_apple_rust': 'Cedar-apple rust is caused by Gymnosporangium juniperi-virginianae, a fungus requiring two hosts — apple and eastern red cedar. On apple, it produces bright orange-yellow spots on the upper leaf surface and tube-like structures underneath, weakening the tree over time.',
    'Apple___healthy': 'The apple plant appears healthy with no visible signs of disease, pest damage, or nutritional deficiency. Leaves are uniformly green, firm, and properly formed.',
    'Blueberry___healthy': 'The blueberry plant appears healthy with no visible disease symptoms. Leaves show normal coloration and structure, indicating good plant health and growth conditions.',
    'Cherry_(including_sour)___Powdery_mildew': 'Powdery mildew on cherry is caused by Podosphaera clandestina. It appears as white, powdery fungal growth on young leaves, shoots, and fruit. Infected leaves curl or pucker and may drop early. The disease is favoured by warm days and cool nights with high humidity.',
    'Cherry_(including_sour)___healthy': 'The cherry plant appears healthy with no signs of disease or pest infestation. Leaves are vibrant green and properly developed.',
    'Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot': 'Gray leaf spot, caused by Cercospora zeae-maydis, is one of the most significant fungal diseases of maize. It produces rectangular, tan to gray lesions that run parallel to leaf veins. Severe infection causes large areas of leaf tissue to die, reducing photosynthesis and grain yield significantly.',
    'Corn_(maize)__Common_rust': 'Common rust is caused by Puccinia sorghi. Small, circular to elongated, golden-brown pustules appear on both leaf surfaces. As the disease progresses, pustules turn dark brown to black. Heavy infections can cause premature leaf death and significant yield loss in susceptible varieties.',
    'Corn_(maize)___Northern_Leaf_Blight': 'Northern leaf blight is caused by Exserohilum turcicum. It produces long, elliptical, grayish-green to tan lesions (5–15 cm) on leaves. The lesions coalesce under severe infection, causing large portions of the leaf to die. It is most severe in cool, moist environments.',
    'Corn_(maize)___healthy': 'The maize plant appears healthy with no visible signs of disease or stress. Leaves are green, upright, and free from lesions or discoloration.',
    'Grape___Black_rot': 'Grape black rot is caused by Guignardia bidwellii. It produces tan or brown circular spots with dark borders on leaves, and infected berries shrivel into hard, black mummies. The disease spreads rapidly in warm, wet conditions and can destroy entire clusters if unmanaged.',
    'Grape__Esca(Black_Measles)': 'Esca, also called black measles, is a complex disease caused by several wood-rotting fungi. It causes tiger-stripe patterns on leaves and internal brown streaking of wood. Berries develop dark spotting. Severely affected vines may collapse suddenly — a condition called apoplexy.',
    'Grape__Leaf_blight(Isariopsis_Leaf_Spot)': 'Isariopsis leaf spot, caused by Pseudocercospora vitis, produces angular, reddish-brown spots on the upper leaf surface with grayish fungal growth below. Severe infection causes early defoliation, reducing photosynthesis and weakening the vine. It is favoured by warm, humid conditions.',
    'Grape___healthy': 'The grapevine appears healthy with no visible symptoms of disease. Leaves are evenly coloured and free of lesions, spots, or deformation.',
    'Orange__Haunglongbing(Citrus_greening)': 'Huanglongbing (HLB), or citrus greening, is caused by the bacterium Candidatus Liberibacter asiaticus and spread by the Asian citrus psyllid. It causes blotchy mottling on leaves, stunted growth, and misshapen, bitter, green fruit. There is currently no cure — infected trees must be removed.',
    'Peach___Bacterial_spot': 'Bacterial spot of peach is caused by Xanthomonas arboricola pv. pruni. It produces water-soaked spots on leaves that turn purple-brown and fall out, creating a shot-hole appearance. Fruit develop sunken, scabby lesions. Wet, windy weather promotes rapid spread.',
    'Peach___healthy': 'The peach plant appears healthy with lush, green foliage and no signs of disease or pest damage.',
    'Pepper,bell__Bacterial_spot': 'Bacterial spot of pepper is caused by Xanthomonas campestris pv. vesicatoria. It produces water-soaked spots on leaves, stems, and fruit that turn brown and scabby. Leaves may yellow and drop. The disease spreads rapidly in warm, wet weather, especially through overhead irrigation or rain.',
    'Pepper,bell__healthy': 'The bell pepper plant appears healthy with no visible disease symptoms, showing normal leaf color, shape, and texture.',
    'Potato___Early_blight': 'Early blight is caused by Alternaria solani. It produces circular, dark brown to black lesions with a characteristic concentric ring pattern (target-board appearance) on older leaves first. Infected leaves yellow and drop. The disease reduces plant vigour and can significantly impact tuber yield.',
    'Potato___Late_blight': 'Late blight, caused by Phytophthora infestans, is the devastating disease responsible for the Irish Potato Famine. It causes rapidly spreading, water-soaked, dark lesions on leaves with white mold on undersides in humid conditions. It can destroy an entire crop within days if conditions are favourable.',
    'Potato___healthy': 'The potato plant appears healthy with no signs of disease. Foliage is green, upright, and free from spots or lesions.',
    'Raspberry___healthy': 'The raspberry plant appears healthy with no visible symptoms of disease or nutrient deficiency. Canes and leaves show normal, vigorous growth.',
    'Soybean___healthy': 'The soybean plant appears healthy with no disease symptoms. Leaves are green, trifoliate, and properly formed, indicating good growing conditions.',
    'Squash___Powdery_mildew': 'Powdery mildew on squash is caused by Podosphaera xanthii or Erysiphe cichoracearum. It appears as white, powdery patches on leaf surfaces, petioles, and stems. Heavily infected leaves turn yellow and die. The disease thrives in warm, dry conditions with high humidity at night.',
    'Strawberry___Leaf_scorch': 'Strawberry leaf scorch is caused by the fungus Diplocarpon earlianum. It produces small, irregular, purplish spots on the upper leaf surface. As spots enlarge, the centres turn brown while the edges remain purple, giving a scorched appearance. Severe infection weakens plants and reduces yields.',
    'Strawberry___healthy': 'The strawberry plant appears healthy with vibrant green leaves and no signs of disease, pests, or nutrient problems.',
    'Tomato___Bacterial_spot': 'Tomato bacterial spot is caused by Xanthomonas species. It produces small, water-soaked spots on leaves, stems, and fruit that turn dark brown with yellow halos. Infected fruit have raised, scabby spots. The disease spreads rapidly in warm, wet conditions and through contaminated seeds.',
    'Tomato___Early_blight': 'Tomato early blight is caused by Alternaria solani. It produces dark brown lesions with concentric rings on older leaves. Surrounding tissue may yellow. As infection progresses, leaves die and drop, reducing plant vigour and fruit size. It is favoured by warm temperatures and leaf wetness.',
    'Tomato___Late_blight': 'Tomato late blight, caused by Phytophthora infestans, produces large, irregular, greasy-looking, brown lesions on leaves and stems. White mold may appear on undersides in humid weather. Fruit develop firm, brown, greasy patches. The disease spreads extremely fast and can destroy crops rapidly.',
    'Tomato___Leaf_Mold': 'Tomato leaf mold is caused by Passalora fulva (formerly Cladosporium fulvum). It produces pale green or yellow spots on the upper leaf surface with an olive-green to brown velvety mold on the undersides. Infected leaves eventually turn yellow and drop. It thrives in high humidity and poorly ventilated greenhouses.',
    'Tomato___Septoria_leaf_spot': 'Septoria leaf spot is caused by Septoria lycopersici. It produces numerous small, circular spots with white or gray centres and dark brown borders on leaves. Tiny black specks (pycnidia) can be seen in spot centres. Infected leaves yellow and drop, starting from the bottom of the plant. It spreads rapidly in warm, wet conditions.',
    'Tomato___Spider_mites Two-spotted_spider_mite': 'Two-spotted spider mites (Tetranychus urticae) are tiny arachnids that feed on the underside of tomato leaves, causing stippling, bronzing, and leaf drop. Severe infestations produce fine webbing on leaves. Hot, dry conditions favour rapid population build-up and extensive damage.',
    'Tomato___Target_Spot': 'Target spot is caused by Corynespora cassiicola. It produces brown, circular lesions with concentric rings on leaves, stems, and fruit. Leaves may yellow and drop. Fruit lesions are sunken and dark. The disease is favoured by warm temperatures and prolonged leaf wetness.',
    'Tomato___Tomato_Yellow_Leaf_Curl_Virus': 'Tomato yellow leaf curl virus (TYLCV) is transmitted by whiteflies (Bemisia tabaci). Infected plants show severe stunting, upward leaf curling, yellowing of leaf margins, and little to no fruit set. There is no cure — infected plants must be removed, and vector (whitefly) control is critical.',
    'Tomato___Tomato_mosaic_virus': 'Tomato mosaic virus (ToMV) causes mottled light and dark green patterns on leaves, distortion, and stunting. Fruit may show uneven ripening and internal browning. The virus spreads through contact with infected plant material, tools, and hands. There is no chemical cure; resistant varieties are the best defence.',
    'Tomato___healthy': 'The tomato plant appears healthy with deep green leaves, no spots, lesions, or deformation. Growth looks vigorous and normal.',
}

prevention_methods = {
    'Apple___Apple_scab': "1. Plant scab-resistant apple varieties.\n2. Rake and destroy fallen leaves to reduce overwintering inoculum.\n3. Prune trees to improve airflow and reduce humidity.\n4. Apply protective fungicides (e.g., captan or mancozeb) from bud break through early summer.\n5. Avoid overhead irrigation.",
    'Apple___Black_rot': "1. Prune and destroy cankered wood and mummified fruit.\n2. Remove dead or dying branches promptly.\n3. Apply copper-based or other recommended fungicides.\n4. Maintain good orchard sanitation by removing fallen debris.\n5. Avoid wounding trees during pruning to limit infection sites.",
    'Apple___Cedar_apple_rust': "1. Remove nearby eastern red cedar or juniper trees if possible.\n2. Plant rust-resistant apple varieties.\n3. Apply fungicides (e.g., myclobutanil or mancozeb) from pink stage through petal fall.\n4. Monitor for bright orange galls on junipers in early spring and remove them.",
    'Apple___healthy': "1. Maintain regular pruning for good canopy airflow.\n2. Follow a balanced fertilisation schedule.\n3. Monitor regularly for early signs of pest or disease.\n4. Apply preventive fungicide sprays if disease pressure is historically high in your area.",
    'Blueberry___healthy': "1. Maintain soil pH between 4.5–5.5 for optimal growth.\n2. Mulch around plants to retain moisture and suppress weeds.\n3. Prune old canes annually to encourage new growth.\n4. Monitor regularly for signs of mummy berry, botrytis, or mites.",
    'Cherry_(including_sour)___Powdery_mildew': "1. Plant mildew-resistant varieties where available.\n2. Prune to improve air circulation within the canopy.\n3. Avoid excessive nitrogen fertilisation which promotes lush, susceptible growth.\n4. Apply sulfur-based or systemic fungicides (e.g., myclobutanil) at first sign of infection.\n5. Remove and destroy infected shoots.",
    'Cherry_(including_sour)___healthy': "1. Ensure proper spacing for good airflow between trees.\n2. Water at the base of the tree and avoid wetting foliage.\n3. Apply a balanced fertiliser in spring.\n4. Scout regularly for brown rot, leaf spot, and pest infestations.",
    'Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot': "1. Plant resistant hybrids — this is the most effective control.\n2. Practice crop rotation (avoid maize-after-maize).\n3. Reduce tillage to bury infected residue.\n4. Apply foliar fungicides (e.g., strobilurin or triazole class) at early tassel stage if infection is detected.\n5. Improve field drainage to reduce humidity.",
    'Corn_(maize)__Common_rust': "1. Plant rust-resistant hybrids.\n2. Apply foliar fungicides (e.g., propiconazole or azoxystrobin) if rust appears before tasselling in susceptible varieties.\n3. Monitor fields regularly, especially in cool, humid weather.\n4. Avoid late planting dates which expose crops to peak rust seasons.",
    'Corn_(maize)___Northern_Leaf_Blight': "1. Use resistant hybrids as the primary management strategy.\n2. Rotate crops to reduce fungal residue in the field.\n3. Apply fungicides (e.g., strobilurin-based) at early tassel stage if disease pressure is high.\n4. Reduce surface residue through tillage where appropriate.\n5. Ensure good drainage to minimise leaf wetness duration.",
    'Corn_(maize)___healthy': "1. Use high-quality certified seed from reputable sources.\n2. Conduct soil tests and apply balanced NPK fertilisation.\n3. Rotate crops to break pest and disease cycles.\n4. Monitor regularly for signs of stress, pest damage, or early disease.",
    'Grape___Black_rot': "1. Remove and destroy mummified berries and infected canes during dormancy.\n2. Apply fungicides (e.g., mancozeb, captan, or myclobutanil) from budbreak through veraison.\n3. Ensure good canopy management to improve air circulation.\n4. Avoid overhead irrigation; use drip irrigation instead.\n5. Practice strict vineyard sanitation.",
    'Grape__Esca(Black_Measles)': "1. There is no cure once vines are infected — focus on prevention.\n2. Protect pruning wounds immediately with wound sealants or fungicides.\n3. Prune during dry conditions to minimise spore infection.\n4. Remove and destroy severely infected vines.\n5. Avoid large pruning cuts; use minimal pruning where possible.",
    'Grape__Leaf_blight(Isariopsis_Leaf_Spot)': "1. Apply copper-based or mancozeb fungicides from early shoot growth.\n2. Improve canopy airflow through proper training and pruning.\n3. Remove and destroy infected leaves and debris at season end.\n4. Avoid overhead watering to reduce leaf wetness.\n5. Monitor vines regularly during warm, humid periods.",
    'Grape___healthy': "1. Maintain proper vine training and canopy management.\n2. Apply balanced nutrition with soil and tissue testing.\n3. Scout regularly for mildew, rot, and pest issues.\n4. Use drip irrigation to keep foliage dry.",
    'Orange__Haunglongbing(Citrus_greening)': "1. There is no cure — remove and destroy infected trees immediately to protect neighbouring trees.\n2. Control the Asian citrus psyllid vector with insecticides.\n3. Use certified disease-free planting material.\n4. Inspect new plantings regularly and establish psyllid monitoring traps.\n5. Support biological control of psyllids using natural predators.",
    'Peach___Bacterial_spot': "1. Plant resistant or tolerant peach varieties.\n2. Apply copper-based bactericides from budbreak at 7–10 day intervals during wet weather.\n3. Prune to improve airflow and reduce humidity in the canopy.\n4. Avoid overhead irrigation.\n5. Remove and destroy heavily infected branches and fruit.",
    'Peach___healthy': "1. Thin fruit to reduce weight stress and improve air circulation.\n2. Apply dormant copper sprays to reduce bacterial and fungal load.\n3. Monitor for borers, scale insects, and leaf curl disease.\n4. Fertilise with a balanced fertiliser in early spring.",
    'Pepper,bell__Bacterial_spot': "1. Use certified disease-free, treated seed.\n2. Apply copper-based bactericides regularly, especially after rain.\n3. Avoid working in fields when plants are wet to reduce spread.\n4. Rotate crops — avoid planting pepper or tomato in the same field for at least 2 years.\n5. Remove and destroy infected plant material promptly.",
    'Pepper,bell__healthy': "1. Ensure consistent watering at the base of the plant.\n2. Apply balanced fertiliser with adequate calcium to prevent blossom-end rot.\n3. Monitor for aphids, thrips, and whiteflies which can vector viral diseases.\n4. Mulch around plants to conserve moisture and reduce soil-splash infection.",
    'Potato___Early_blight': "1. Rotate crops — avoid planting potato or tomato in the same field for 2–3 years.\n2. Use certified, disease-free seed potatoes.\n3. Apply fungicides (e.g., chlorothalonil, mancozeb) preventively when conditions favour disease.\n4. Remove infected leaves and plant debris after harvest.\n5. Maintain good plant nutrition — stressed plants are more susceptible.",
    'Potato___Late_blight': "1. Plant certified, blight-resistant varieties.\n2. Apply preventive fungicides (e.g., chlorothalonil, metalaxyl, or cymoxanil) before and during wet weather.\n3. Destroy volunteer potato plants and cull piles.\n4. Avoid overhead irrigation and harvest in dry conditions.\n5. Monitor weather forecasts — late blight risk is highest when nights are cool and days are warm and wet.",
    'Potato___healthy': "1. Use certified disease-free seed tubers.\n2. Hill up soil around plants to protect developing tubers.\n3. Maintain consistent soil moisture to avoid stress cracking.\n4. Scout regularly for aphids (virus vectors), Colorado potato beetle, and early disease signs.",
    'Raspberry___healthy': "1. Prune out old fruiting canes after harvest to improve airflow.\n2. Train canes on a trellis to keep them off the ground.\n3. Mulch around the base to retain moisture and suppress weeds.\n4. Monitor for cane blight, spur blight, and spider mites.",
    'Soybean___healthy': "1. Use certified, treated seed from reputable sources.\n2. Inoculate seed with Rhizobium bacteria to fix atmospheric nitrogen.\n3. Rotate with non-legume crops to break soybean cyst nematode and fungal cycles.\n4. Scout for aphids, stink bugs, and sudden death syndrome symptoms.",
    'Squash___Powdery_mildew': "1. Plant resistant varieties when available.\n2. Apply fungicides (e.g., sulfur, potassium bicarbonate, or neem oil) at first sign of infection.\n3. Improve air circulation by proper plant spacing.\n4. Avoid excessive nitrogen fertilisation.\n5. Water at the base of the plant in the morning so foliage stays dry.",
    'Strawberry___Leaf_scorch': "1. Remove and destroy infected leaves promptly.\n2. Apply fungicides (e.g., captan or myclobutanil) during wet weather periods.\n3. Improve airflow through proper plant spacing and row orientation.\n4. Avoid overhead irrigation; use drip irrigation.\n5. Renovate beds after harvest by mowing foliage and removing debris.",
    'Strawberry___healthy': "1. Renovate plantings after harvest to rejuvenate beds.\n2. Use drip irrigation to keep foliage dry.\n3. Apply balanced fertiliser in spring and after renovation.\n4. Monitor for grey mold (Botrytis), angular leaf spot, and two-spotted spider mites.",
    'Tomato___Bacterial_spot': "1. Use certified disease-free seed; treat seed with hot water before planting.\n2. Apply copper-based bactericides regularly, especially after rain or overhead irrigation.\n3. Rotate crops — avoid tomato and pepper in the same field for 2+ years.\n4. Avoid working in wet fields.\n5. Remove and destroy infected plant debris at end of season.",
    'Tomato___Early_blight': "1. Rotate crops to reduce soilborne inoculum.\n2. Use mulch to prevent soil-splash onto lower leaves.\n3. Remove and destroy infected lower leaves early.\n4. Apply fungicides (e.g., chlorothalonil, mancozeb) preventively during warm, wet weather.\n5. Water at the base of the plant, not overhead.",
    'Tomato___Late_blight': "1. Plant resistant varieties.\n2. Apply fungicides (e.g., chlorothalonil, metalaxyl, or cymoxanil) before and during wet, cool weather.\n3. Destroy all infected plant debris, cull piles, and volunteer plants.\n4. Avoid overhead irrigation.\n5. Monitor regional disease alerts and spray preventively when late blight is reported nearby.",
    'Tomato___Leaf_Mold': "1. Ensure good greenhouse ventilation to reduce humidity below 85%.\n2. Remove and destroy infected leaves.\n3. Apply fungicides (e.g., chlorothalonil or copper-based products).\n4. Use drip irrigation instead of overhead watering.\n5. Space plants adequately and train vertically for better airflow.",
    'Tomato___Septoria_leaf_spot': "1. Rotate crops — do not plant tomato in the same location for 2–3 years.\n2. Remove and destroy infected leaves at first sign.\n3. Apply fungicides (e.g., chlorothalonil, mancozeb, or copper) preventively during wet weather.\n4. Mulch to prevent soil-splash.\n5. Stake and tie plants to improve airflow and keep foliage off the ground.",
    'Tomato___Spider_mites Two-spotted_spider_mite': "1. Maintain adequate plant hydration — water-stressed plants are more susceptible.\n2. Use miticides (e.g., abamectin, bifenazate) when populations are high.\n3. Introduce biological controls like predatory mites (Phytoseiidae).\n4. Spray the undersides of leaves with a strong jet of water to dislodge mites.\n5. Avoid excessive use of broad-spectrum insecticides which kill natural predators.",
    'Tomato___Target_Spot': "1. Remove infected leaves and plant debris regularly.\n2. Apply fungicides (e.g., chlorothalonil or azoxystrobin) at first sign of disease.\n3. Improve air circulation through proper spacing and staking.\n4. Avoid overhead irrigation and keep foliage dry.\n5. Rotate crops to reduce soilborne inoculum.",
    'Tomato___Tomato_Yellow_Leaf_Curl_Virus': "1. Control whitefly populations using insecticides (e.g., imidacloprid) or yellow sticky traps.\n2. Use reflective mulches to deter whiteflies.\n3. Plant resistant or tolerant varieties (e.g., those carrying Ty genes).\n4. Remove and destroy infected plants immediately to prevent further spread.\n5. Avoid planting near other infected hosts like weeds or older tomato crops.",
    'Tomato___Tomato_mosaic_virus': "1. Use certified virus-free seed or treat seed with 10% trisodium phosphate solution.\n2. Wash hands thoroughly and sterilise tools between plants to prevent mechanical spread.\n3. Plant resistant varieties.\n4. Remove and destroy infected plants immediately.\n5. Control aphid vectors and avoid using tobacco products near plants (tobacco can carry the virus).",
    'Tomato___healthy': "1. Maintain consistent soil moisture with mulching and drip irrigation.\n2. Apply balanced NPK fertiliser with adequate calcium and magnesium.\n3. Scout weekly for early signs of pests, blight, or viral symptoms.\n4. Stake or cage plants to improve airflow and keep foliage off the ground.",
}

model = load_model("dataset/best_model.h5")

def prediction(path):
    img = load_img(path, target_size=(224, 224))
    i = img_to_array(img)
    im = preprocess_input(i)
    img = np.expand_dims(im, axis=0)
    pred = np.argmax(model.predict(img))
    label = label_mapping.get(pred, 'Unknown disease')   # 🔥 SAFE: avoids KeyError
    return label

def upload(request):
    if request.method == "POST":
        images = request.FILES['Images']
        s = images_data(Images=images)
        s.save()
        return redirect("predict")
    return HttpResponse("Fail")

def predict(request):
    img = images_data.objects.last()
    image_path = str(img.Images.url).replace("/media", "media")
    predicted_label = prediction(image_path)
    predicted_description = label_descriptions.get(predicted_label, "Description not available.")
    prevention = prevention_methods.get(predicted_label, "Prevention Not Found.")
    ctx = {
        'image': img,
        'predicted_label': predicted_label,
        'predicted_description': predicted_description,
        'prevention': prevention
    }
    ctx.update(get_user_context(request))
    return render(request, 'predict.html', ctx)

# ─── NEWS ───────────────────────────────────────────────
def news(request):
    ctx = {'navbar': 'home'}
    ctx.update(get_user_context(request))
    return render(request, "news.html", ctx)

def search_news(request):
    import requests
    from django.http import JsonResponse
    query = request.GET.get('query', '')
    if not query:
        return JsonResponse([])
    api_url = f"https://newsapi.org/v2/everything?q={query}&apiKey=ef1fdd0440c648f286f01347733fc54d"
    try:
        response = requests.get(api_url)
        data = response.json()
        articles = []
        if data.get("status") == "ok":
            for article in data.get("articles", []):
                articles.append({
                    "title": article.get("title"),
                    "description": article.get("description"),
                    "url": article.get("url"),
                })
        return JsonResponse(articles, safe=False)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

# ─── E‑MARKETPLACE (farmer side) ────────────────────────
@login_required(login_url="log_in")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def e_market(request):
    all_listings = image_data.objects.all().order_by('-id')
    my_listings = image_data.objects.filter(user=request.user).order_by('-id')
    context = {
        'images': all_listings,
        'my_listings': my_listings,
        'first_name': request.user.first_name,
        'last_name': request.user.last_name,
    }
    return render(request, "e_market.html", context)

@login_required(login_url="log_in")
def upload_crop_image(request):
    if request.method == 'POST':
        image_file = request.FILES.get('crop_image')
        quantity = request.POST.get('quantity')
        crop_type = request.POST.get('crop_type', '')
        price = request.POST.get('price') or None
        location = request.POST.get('location', '')
        notes = request.POST.get('notes', '')
        if image_file and quantity and crop_type and price:
            image_data.objects.create(
                user=request.user,
                Images=image_file,
                quantity=int(quantity),
                crop_type=crop_type,
                price=float(price),
                location=location,
                notes=notes
            )
            messages.success(request, "Crop listed successfully!")
        else:
            messages.error(request, "Please fill all required fields (crop type, quantity, price).")
        return redirect('e_market')
    return render(request, 'upload_crop_image.html')

@login_required(login_url="log_in")
def delete_listing(request, item_id):
    listing = get_object_or_404(image_data, id=item_id, user=request.user)
    if request.method == 'POST':
        listing.delete()
        messages.success(request, "Listing removed from marketplace.")
    return redirect('e_market')

# ─── VENDOR AUTH ────────────────────────────────────────
def vendor_register(request):
    if request.method == "POST":
        first_name = request.POST['first_name']
        last_name = request.POST['last_name']
        phone_number = request.POST['phone_number']
        email = request.POST['username']
        password = request.POST['password']
        password1 = request.POST['password1']
        if password != password1:
            messages.error(request, "Passwords do not match.")
            return redirect("vendor_register")
        if Vendor.objects.filter(email=email).exists():
            messages.error(request, "Vendor with this email already exists.")
            return redirect("vendor_register")
        Vendor.objects.create(
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number,
            email=email,
            password=make_password(password)
        )
        messages.success(request, "Vendor registration successful.")
        return redirect("vendor_log_in")
    return render(request, "vendor_register.html")

def vendor_log_in(request):
    if request.method == "POST":
        email = request.POST['username']
        password = request.POST['password']
        try:
            vendor = Vendor.objects.get(email=email)
            if check_password(password, vendor.password):
                request.session['vendor_id'] = vendor.id
                request.session['cart'] = []
                request.session.modified = True
                messages.success(request, "Vendor login successful.")
                return redirect("vendor_dashboard")
            else:
                raise Vendor.DoesNotExist
        except Vendor.DoesNotExist:
            messages.error(request, "Invalid email or password.")
            return redirect("vendor_log_in")
    return render(request, "vendor_log_in.html")

# ─── VENDOR EDIT PROFILE ────────────────────────────────
def vendor_edit_profile(request):
    vendor_id = request.session.get('vendor_id')
    if not vendor_id:
        messages.error(request, "Please log in first.")
        return redirect('vendor_log_in')
    vendor = Vendor.objects.get(id=vendor_id)

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name  = request.POST.get('last_name', '').strip()
        phone      = request.POST.get('phone', '').strip()
        old_pw     = request.POST.get('old_password', '')
        new_pw     = request.POST.get('new_password', '')

        if not first_name or not last_name:
            messages.error(request, "First and last name are required.")
        else:
            vendor.first_name   = first_name
            vendor.last_name    = last_name
            vendor.phone_number = phone
            vendor.save()
            messages.success(request, "Profile updated.")

        if old_pw and new_pw:
            if check_password(old_pw, vendor.password):
                if len(new_pw) >= 8:
                    vendor.password = make_password(new_pw)
                    vendor.save()
                    messages.success(request, "Password changed. Please log in again.")
                    request.session.pop('vendor_id', None)
                    return redirect('vendor_log_in')
                else:
                    messages.error(request, "New password must be at least 8 characters.")
            else:
                messages.error(request, "Old password is incorrect.")
        elif old_pw or new_pw:
            messages.error(request, "Fill both password fields to change password.")

        return render(request, 'vendor_edit_profile.html', {'vendor': vendor})

    return render(request, 'vendor_edit_profile.html', {'vendor': vendor})

# ─── VENDOR DASHBOARD & CART ────────────────────────────
def vendor_dashboard(request):
    vendor_id = request.session.get('vendor_id')
    if not vendor_id:
        messages.error(request, "Please log in first.")
        return redirect("vendor_log_in")
    vendor = Vendor.objects.get(id=vendor_id)
    images = image_data.objects.all().select_related('user')
    cart_ids = request.session.get('cart', [])
    cart_items = image_data.objects.filter(id__in=cart_ids)
    vendor_inquiries = Inquiry.objects.filter(vendor=vendor).order_by('-created_at')
    return render(request, 'vendor_dashboard.html', {
        'vendor': vendor,
        'images': images,
        'cart_items': cart_items,
        'vendor_inquiries': vendor_inquiries,
    })

def add_to_cart(request, item_id):
    if request.method == "POST":
        cart = request.session.get('cart', [])
        if item_id not in cart:
            cart.append(item_id)
        request.session['cart'] = cart
        messages.success(request, "Item added to cart.")
    return redirect('vendor_dashboard')

def remove_from_cart(request, item_id):
    if request.method == 'POST':
        cart = request.session.get('cart', [])
        cart = [i for i in cart if str(i) != str(item_id)]
        request.session['cart'] = cart
        messages.success(request, "Item removed from cart.")
    return redirect('vendor_dashboard')

# ─── INQUIRY VIEWS ─────────────────────────────────────
def send_listing_inquiry(request, listing_id):
    if request.method == 'POST':
        vendor_id = request.session.get('vendor_id')
        if not vendor_id:
            messages.error(request, "Please log in as vendor.")
            return redirect('vendor_log_in')
        vendor = Vendor.objects.get(id=vendor_id)
        listing = get_object_or_404(image_data, id=listing_id)
        farmer = listing.user
        message = request.POST.get('message', '').strip()
        if not message:
            messages.error(request, "Please write a message.")
            return redirect('vendor_dashboard')

        Inquiry.objects.create(
            vendor=vendor,
            farmer=farmer,
            listing=listing,
            message=message,
            direction='VF'
        )

        subject = f"Purchase Inquiry: {listing.crop_type} - AgriSmart"
        body = f"""Hello {farmer.get_full_name() or farmer.username},

You have a new purchase inquiry from {vendor.first_name} {vendor.last_name} ({vendor.email}) regarding your listing:

Crop: {listing.crop_type}
Quantity: {listing.quantity} KG
Price: ₹{listing.price}/kg (total: ₹{listing.price * listing.quantity})
Location: {listing.location if listing.location else 'Not specified'}

Message:
{message}

Please log in to your AgriSmart dashboard to view and respond.

Regards,
AgriSmart Team
"""
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [farmer.email], fail_silently=False)
        messages.success(request, f"Inquiry sent to {farmer.get_full_name() or farmer.username}!")
        return redirect('vendor_dashboard')
    return redirect('vendor_dashboard')

def send_cart_inquiry(request):
    if request.method == 'POST':
        vendor_id = request.session.get('vendor_id')
        if not vendor_id:
            messages.error(request, "Please log in as vendor.")
            return redirect('vendor_log_in')
        vendor = Vendor.objects.get(id=vendor_id)
        cart_ids = request.session.get('cart', [])
        if not cart_ids:
            messages.error(request, "Your cart is empty.")
            return redirect('vendor_dashboard')
        listings = image_data.objects.filter(id__in=cart_ids)
        message = request.POST.get('cart_message', '').strip()
        if not message:
            messages.error(request, "Please include a message.")
            return redirect('vendor_dashboard')

        farmer_map = {}
        for listing in listings:
            farmer = listing.user
            if farmer not in farmer_map:
                farmer_map[farmer] = []
            farmer_map[farmer].append(listing)

        for farmer, items in farmer_map.items():
            for item in items:
                Inquiry.objects.create(
                    vendor=vendor,
                    farmer=farmer,
                    listing=item,
                    message=message,
                    direction='VF'
                )
            items_text = ""
            for item in items:
                items_text += f"- {item.crop_type}: {item.quantity} KG @ ₹{item.price}/kg (Total: ₹{item.price * item.quantity})\n"

            subject = f"Purchase Inquiry for {len(items)} listing(s) - AgriSmart"
            body = f"""Hello {farmer.get_full_name() or farmer.username},

{vendor.first_name} {vendor.last_name} ({vendor.email}) has sent you a purchase inquiry for the following listings:

{items_text}

Message from vendor:
{message}

Please log in to your AgriSmart dashboard to view and respond.

Regards,
AgriSmart Team
"""
            send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [farmer.email], fail_silently=False)

        request.session['cart'] = []
        messages.success(request, "Purchase inquiries sent to all farmers! Your cart is now empty.")
        return redirect('vendor_dashboard')
    return redirect('vendor_dashboard')

# ─── FARMER REPLY ──────────────────────────────────────
@login_required(login_url="log_in")
def reply_inquiry(request, inquiry_id):
    if request.method == 'POST':
        original = get_object_or_404(Inquiry, id=inquiry_id, farmer=request.user)
        reply_text = request.POST.get('reply', '').strip()
        if not reply_text:
            messages.error(request, "Please write a reply.")
            return redirect('dashboard')

        Inquiry.objects.create(
            vendor=original.vendor,
            farmer=request.user,
            listing=original.listing,
            message=reply_text,
            direction='FV'
        )

        subject = f"Reply from {request.user.get_full_name() or request.user.username}: {original.listing.crop_type}"
        body = f"Hello {original.vendor.first_name},\n\n{request.user.get_full_name() or request.user.username} replied to your inquiry:\n\n{reply_text}\n\nContact: {request.user.email}"
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [original.vendor.email], fail_silently=False)

        messages.success(request, "Reply sent to vendor!")
        return redirect('dashboard')
    return redirect('dashboard')

# ─── VENDOR REPLY ───────────────────────────────────────
def vendor_reply_inquiry(request, inquiry_id):
    if request.method == 'POST':
        vendor_id = request.session.get('vendor_id')
        if not vendor_id:
            messages.error(request, "Please log in as vendor.")
            return redirect('vendor_log_in')
        vendor = Vendor.objects.get(id=vendor_id)
        original = get_object_or_404(Inquiry, id=inquiry_id, vendor=vendor)
        reply_text = request.POST.get('vendor_reply', '').strip()
        if not reply_text:
            messages.error(request, "Please write a reply.")
            return redirect('vendor_dashboard')

        Inquiry.objects.create(
            vendor=vendor,
            farmer=original.farmer,
            listing=original.listing,
            message=reply_text,
            direction='VF'
        )

        subject = f"New reply from {vendor.first_name} - {original.listing.crop_type}"
        body = f"Hello {original.farmer.get_full_name() or original.farmer.username},\n\n{vendor.first_name} {vendor.last_name} replied:\n\n{reply_text}\n\nView on AgriSmart dashboard."
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [original.farmer.email], fail_silently=False)

        messages.success(request, "Reply sent to farmer!")
        return redirect('vendor_dashboard')
    return redirect('vendor_dashboard')

# ─── DELETE INQUIRIES ───────────────────────────────────
@login_required(login_url="log_in")
def delete_inquiry(request, inquiry_id):
    inquiry = get_object_or_404(Inquiry, id=inquiry_id, farmer=request.user)
    if request.method == 'POST':
        inquiry.delete()
        messages.success(request, "Inquiry removed.")
    return redirect('dashboard')

def delete_vendor_inquiry(request, inquiry_id):
    vendor_id = request.session.get('vendor_id')
    if not vendor_id:
        messages.error(request, "Please log in as vendor.")
        return redirect('vendor_log_in')
    vendor = Vendor.objects.get(id=vendor_id)
    inquiry = get_object_or_404(Inquiry, id=inquiry_id, vendor=vendor)
    if request.method == 'POST':
        inquiry.delete()
        messages.success(request, "Conversation removed.")
    return redirect('vendor_dashboard')

# ─── PASSWORD RESET FLOW ────────────────────────────────
@csrf_exempt
def send_reset_otp(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        if not email:
            return JsonResponse({'status': 'error', 'message': 'Email is required.'}, status=400)

        user_exists = User.objects.filter(email=email).exists() or User.objects.filter(username=email).exists()
        vendor_exists = Vendor.objects.filter(email=email).exists()

        if not user_exists and not vendor_exists:
            return JsonResponse({'status': 'error', 'message': 'No account found with this email.'}, status=404)

        otp = str(random.randint(100000, 999999))
        PasswordResetOTP.objects.filter(email=email).delete()
        expires = now() + timedelta(minutes=10)
        PasswordResetOTP.objects.create(email=email, otp=otp, expiry_time=expires)

        html_message = f"""
        <html>
        <body style="background:#f5f5f0; margin:0; padding:40px; font-family:Arial, sans-serif;">
          <div style="max-width:480px; margin:0 auto; background:#ffffff; border:1px solid #d4b30a; border-radius:16px; padding:40px; text-align:center;">
            <h1 style="color:#1e6b10; font-size:24px;">AgriSmart</h1>
            <p style="color:#6b8c45; font-size:14px;">Password Reset Verification</p>
            <div style="background:rgba(45,143,28,0.06); border:1px solid rgba(45,143,28,0.2); border-radius:12px; padding:24px; margin:24px 0;">
              <p style="font-size:16px; color:#0f1e05;">Your verification code:</p>
              <h2 style="color:#1e6b10; font-size:36px; letter-spacing:8px; font-family:monospace;">{otp}</h2>
              <p style="font-size:13px; color:#9aaa72;">Valid for <strong>10 minutes</strong> only.</p>
            </div>
            <p style="font-size:12px; color:#9aaa72;">If you did not request this, please ignore.<br>AgriSmart Support</p>
          </div>
        </body>
        </html>
        """
        plain_message = f"Your AgriSmart OTP is: {otp}. Valid for 10 minutes."

        subject = "🔑 AgriSmart Password Reset OTP"
        mail = EmailMultiAlternatives(subject, strip_tags(plain_message), settings.DEFAULT_FROM_EMAIL, [email])
        mail.attach_alternative(html_message, "text/html")
        mail.send(fail_silently=False)

        return JsonResponse({'status': 'success', 'message': 'OTP sent to your email.'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request.'}, status=400)

@csrf_exempt
def verify_reset_otp(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        otp = request.POST.get('otp', '').strip()
        if not email or not otp:
            return JsonResponse({'status': 'error', 'message': 'Email and OTP required.'}, status=400)

        try:
            record = PasswordResetOTP.objects.filter(email=email, otp=otp, is_used=False).latest('created_at')
        except PasswordResetOTP.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Invalid OTP.'}, status=400)

        if record.expiry_time < now():
            return JsonResponse({'status': 'error', 'message': 'OTP has expired. Please request a new one.'}, status=400)

        record.is_used = True
        record.save()

        request.session['reset_email'] = email
        request.session.modified = True

        return JsonResponse({'status': 'success', 'message': 'OTP verified.'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request.'}, status=400)

@csrf_exempt
def reset_password(request):
    if request.method == 'POST':
        email = request.session.get('reset_email')
        if not email:
            return JsonResponse({'status': 'error', 'message': 'Session expired. Please restart.'}, status=400)

        new_password = request.POST.get('new_password', '')
        if len(new_password) < 8:
            return JsonResponse({'status': 'error', 'message': 'Password must be at least 8 characters.'}, status=400)

        try:
            user = User.objects.get(email=email)
            user.set_password(new_password)
            user.save()
            del request.session['reset_email']
            return JsonResponse({'status': 'success', 'message': 'Password updated! You can now login.'})
        except User.DoesNotExist:
            try:
                user = User.objects.get(username=email)
                user.set_password(new_password)
                user.save()
                del request.session['reset_email']
                return JsonResponse({'status': 'success', 'message': 'Password updated! You can now login.'})
            except User.DoesNotExist:
                pass

        try:
            vendor = Vendor.objects.get(email=email)
            vendor.password = make_password(new_password)
            vendor.save()
            del request.session['reset_email']
            return JsonResponse({'status': 'success', 'message': 'Password updated! You can now login.'})
        except Vendor.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Account not found.'}, status=404)

    return JsonResponse({'status': 'error', 'message': 'Invalid request.'}, status=400)