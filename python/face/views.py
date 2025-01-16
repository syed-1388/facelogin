import os
import base64
import json
import logging
from django.conf import settings
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.http import JsonResponse
from django.shortcuts import render, redirect

from django.views.decorators.csrf import csrf_exempt
from deepface import DeepFace
from .models import Login

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('debug.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def handle_uploaded_face(face_image_data, username, purpose='register'):
    """Helper function to handle face image upload."""
    if face_image_data.startswith('data:image/png;base64,'):
        face_image_data = face_image_data.split(",")[1]

    try:
        image_data = base64.b64decode(face_image_data)
        return ContentFile(image_data, name=f'{username}_{purpose}_face.jpg')
    except Exception as e:
        logger.error(f"Error processing face image: {str(e)}")
        raise ValueError("Invalid image data")


@csrf_exempt
def index(request):
    """Registration view with face capture."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8'))
            username = data.get('username')
            password = data.get('password')
            confirm_password = data.get('confirm_password')
            face_image_data = data.get('face_image')

            # Validation
            if not all([username, password, confirm_password, face_image_data]):
                return JsonResponse({'status': 'error', 'message': 'All fields are required'})

            if password != confirm_password:
                return JsonResponse({'status': 'error', 'message': 'Passwords do not match'})

            if User.objects.filter(username=username).exists():
                return JsonResponse({'status': 'error', 'message': 'Username already taken'})

            # Process face image
            face_image = handle_uploaded_face(face_image_data, username)

            # Create user and face image record
            user = User.objects.create(username=username, password=make_password(password))
            Login.objects.create(user=user, images=face_image)

            logger.info(f"User registered successfully: {username}")
            return JsonResponse({'status': 'success', 'message': 'Registration successful'})

        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            return JsonResponse({'status': 'error', 'message': 'Registration failed'})

    return render(request, 'register.html')


@csrf_exempt
def login_view(request):
    """Login view with face verification."""
    if request.method == 'POST':
        try:
            # Get data from the POST request
            data = json.loads(request.body.decode('utf-8'))
            username = data.get('username')
            face_image_data = data.get('face_image')

            # Check if both username and face image data are provided
            if not all([username, face_image_data]):
                return JsonResponse({'status': 'error', 'message': 'Username and face image are required'})

            # Fetch the user and associated login entry
            try:
                user = User.objects.get(username=username)
                user_login = Login.objects.get(user=user)
            except User.DoesNotExist:
                logger.error(f"User {username} does not exist.")
                return JsonResponse({'status': 'error', 'message': 'User does not exist'})
            except Login.DoesNotExist:
                logger.error(f"Login entry for user {username} does not exist.")
                return JsonResponse({'status': 'error', 'message': 'Login entry not found'})

            # Process and verify the uploaded face image
            try:
                uploaded_face = handle_uploaded_face(face_image_data, username, purpose='login')
                temp_path = os.path.join(settings.MEDIA_ROOT, f'temp_{username}_login.jpg')

                # Save the face image temporarily to disk
                with open(temp_path, 'wb') as temp_file:
                    temp_file.write(uploaded_face.read())

                # Perform face verification using DeepFace
                verification = DeepFace.verify(
                    temp_path,
                    user_login.images.path,
                    enforce_detection=True,
                    detector_backend='retinaface'
                )

                # Clean up the temporary face image file
                os.remove(temp_path)

                # Check if the face verification was successful
                if verification.get('verified'):
                    login(request, user)  # Log the user in
                    logger.info(f"User {username} logged in successfully")
                    return JsonResponse({'status': 'success', 'message': 'Login successful', 'redirect_url': '/profile'})  # Send redirect URL
                else:
                    logger.error(f"Face verification failed for user {username}")
                    return JsonResponse({'status': 'error', 'message': 'Face verification failed'})

            except Exception as e:
                logger.error(f"Face verification error: {str(e)}")
                return JsonResponse({'status': 'error', 'message': 'Face verification failed due to an error'})

        except json.JSONDecodeError:
            logger.error("Failed to decode JSON data.")
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON format'})
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            return JsonResponse({'status': 'error', 'message': 'An error occurred. Please try again.'})

    # For GET request, render the login page
    return render(request, 'login.html')  # Fixed closing parenthesis


@login_required
def profile_view(request):
    """Protected profile view."""
    return render(request, 'profile.html', {'user': request.user})


def logout_view(request):
    """Logout view."""
    logout(request)
    logger.info(f"User logged out: {request.user.username}")
    return redirect('login')