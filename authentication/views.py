# backend/authentication/views.py
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.core.mail import send_mail
from django.contrib.auth import authenticate

from document.models import Hospital
from document.serializers import DoctorSerializer

from .models import Patient
from .serializers import PatientSerializer
from rest_framework import viewsets, permissions
from rest_framework import filters
from .serializers import CreateDoctorSerializer
from django_filters.rest_framework import DjangoFilterBackend 
from rest_framework.permissions import IsAuthenticated
import secrets
from .serializers import (
    UserRegistrationSerializer, 
    LoginSerializer, 
    OTPVerificationSerializer
)
from .models import CustomUser
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import CreateDoctorSerializer
import time
import threading
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags
from rest_framework.throttling import UserRateThrottle,AnonRateThrottle
from rest_framework.throttling import ScopedRateThrottle

class UserRegistrationView(APIView):
    throttle_classes = [AnonRateThrottle]    
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        print(f"🔍 Received registration request for email: {email}")  # Debugging

        # Restrict registration to pre-created users
        user = get_object_or_404(CustomUser, email=email)

        if user.is_active:
            return Response({'error': 'This user is already registered.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = UserRegistrationSerializer(user, data=request.data, partial=True)
        if not serializer.is_valid():
            print(f"❌ Validation errors: {serializer.errors}")  # Debugging
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer.save()
        return Response({'message': 'User registered successfully. Please login.'}, status=status.HTTP_201_CREATED)



FAILED_LOGIN_ATTEMPTS = {}
LOGIN_LOCKOUT_TIMES = [60, 180, 300]  # 1 min, 3 min, 5 min
class LoginView(APIView):
    throttle_classes = [AnonRateThrottle]
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']
            
            if email in FAILED_LOGIN_ATTEMPTS and FAILED_LOGIN_ATTEMPTS[email]['locked_until'] > time.time():
                time_left = FAILED_LOGIN_ATTEMPTS[email]['locked_until'] - time.time()
                return Response({"error": "Too many failed attempts. Try again later.", "lockout_time": int(time_left)}, status=status.HTTP_403_FORBIDDEN)            
            user = authenticate(email=email, password=password)
            
            if user:
                FAILED_LOGIN_ATTEMPTS.pop(email, None)
                otp = user.generate_otp()
                # send_mail(
                #     'Your OTP Code',
                #     f'Your OTP is: {otp}',
                #     'bahahembeirik@gmail.com',
                #     [email],
                #     fail_silently=False,
                # )
                    # Define the email subject with branding
                subject = 'Your OTP Code - MediPlus'

                # Create the HTML content with inline CSS for the blue header and MediPlus branding
                html_content = f"""
                    <html>
                    <head>
                    <style>
                        body {{
                        margin: 0;
                        padding: 0;
                        background-color: #f9f9f9;
                        }}
                        .container {{
                        width: 100%;
                        max-width: 600px;
                        margin: 40px auto;
                        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
                        background-color: #ffffff;
                        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
                        border-radius: 8px;
                        overflow: hidden;
                        }}
                        .header {{
                        background-color: #007BFF;
                        color: #ffffff;
                        padding: 20px;
                        text-align: center;
                        }}
                        .header h1 {{
                        margin: 0;
                        font-size: 28px;
                        letter-spacing: 1px;
                        }}
                        .content {{
                        padding: 20px;
                        line-height: 1.6;
                        color: #333333;
                        }}
                        .content p {{
                        margin: 0 0 16px;
                        }}
                        .otp-code {{
                        text-align: center;
                        font-size: 24px;
                        font-weight: bold;
                        letter-spacing: 2px;
                        color: #007BFF;
                        margin: 20px 0;
                        }}
                        .footer {{
                        background-color: #f1f1f1;
                        padding: 10px;
                        font-size: 12px;
                        text-align: center;
                        color: #777777;
                        }}
                    </style>
                    </head>
                    <body>
                    <div class="container">
                        <div class="header">
                        <h1>MediPlus</h1>
                        </div>
                        <div class="content">
                        <p>Bonjour,</p>
                        <p>Nous sommes ravis de vous accompagner dans votre démarche de connexion sécurisée. Veuillez utiliser le mot de passe à usage unique (OTP) ci-dessous pour finaliser votre connexion :</p>
                        <p class="otp-code">{otp}</p>
                        <p>Si vous n’êtes pas à l’origine de cette demande, veuillez ignorer ce message.</p>
                        <p>Merci d’avoir choisi MediPlus.</p>
                        </div>
                        <div class="footer">
                        <p>&copy; 2025 MediPlus. Tous droits réservés.</p>
                        </div>
                    </div>
                    </body>
                    </html>
                    """


                # Generate a plain text version by stripping the HTML tags
                text_content = strip_tags(html_content)

                # Create the multi-part email message
                msg = EmailMultiAlternatives(
                    subject,
                    text_content,
                    'bahahembeirik@gmail.com',  # Sender's email address
                    [email],
                )

                # Attach the HTML alternative content
                msg.attach_alternative(html_content, "text/html")
                def _send():
                    try:
                        msg.send(fail_silently=False)
                    except Exception as e:
                        print(f"⚠️ Email sending failed: {e}")
                        print(f"🔑 OTP for {email}: {otp}")
                threading.Thread(target=_send, daemon=True).start()
                return Response({'message': 'OTP sent to your email', 'email': email, 'otp': otp}, status=status.HTTP_200_OK)
            
            attempts = FAILED_LOGIN_ATTEMPTS.get(email, {'count': 0, 'locked_until': 0})
            attempts['count'] += 1
            if attempts['count'] >= 3:
                lock_time = LOGIN_LOCKOUT_TIMES[min(attempts['count'] - 3, len(LOGIN_LOCKOUT_TIMES) - 1)]
                attempts['locked_until'] = time.time() + lock_time
            FAILED_LOGIN_ATTEMPTS[email] = attempts
            
            return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class AllPatientsViewSet(viewsets.ViewSet):
    throttle_classes = [UserRateThrottle]

    """
    Example: returns all patients without pagination
    """
    def list(self, request):
        patients = Patient.objects.all()
        serializer = PatientSerializer(patients, many=True)
        return Response(serializer.data)

class OTPVerificationView(APIView):
    throttle_classes = [AnonRateThrottle]

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = OTPVerificationSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            otp = serializer.validated_data['otp']
            
            try:
                user = CustomUser.objects.get(email=email)
                
                if user.verify_otp(otp):
                    # Generate JWT tokens
                    refresh = RefreshToken.for_user(user)
                    
                    return Response({
                        'refresh': str(refresh),
                        'access': str(refresh.access_token),
                        'user_id': user.id,
                        'role': user.role,
                        'message': 'Login successful'
                    }, status=status.HTTP_200_OK)
                
                return Response({
                    'error': 'Invalid or expired OTP'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            except CustomUser.DoesNotExist:
                return Response({
                    'error': 'User not found'
                }, status=status.HTTP_404_NOT_FOUND)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CreateDoctorView(APIView):
    throttle_classes = [UserRateThrottle]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.role != 'Admin':
            return Response({'error': 'Only Admin can create doctors'}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = CreateDoctorSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            hospital = serializer.validated_data['hospital']
            
            # Check if email already exists
            if CustomUser.objects.filter(email=email).exists():
                return Response({'error': 'A doctor with this email already exists.'}, status=status.HTTP_400_BAD_REQUEST)

            # Generate OTP for registration
            doctor = CustomUser.objects.create(
                email=email,
                role='Doctor',
                hospital=hospital,
                is_active=False  # Make doctor inactive until registration is complete
            )

            otp = doctor.generate_otp()

            # Get the first allowed frontend URL from CORS settings
            FRONTEND_URL = settings.CORS_ALLOWED_ORIGINS[0]
            registration_link = f"{FRONTEND_URL}/register?email={email}"    
            subject = 'Your OTP Code - MediPlus'        
            # Send email with registration link
            html_content = f"""
            <html>
            <head>
            <style>
                body {{
                margin: 0;
                padding: 0;
                background-color: #f9f9f9;
                }}
                .container {{
                width: 100%;
                max-width: 600px;
                margin: 40px auto;
                font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
                background-color: #ffffff;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
                border-radius: 8px;
                overflow: hidden;
                }}
                .header {{
                background-color: #007BFF;
                color: #ffffff;
                padding: 20px;
                text-align: center;
                }}
                .header h1 {{
                margin: 0;
                font-size: 28px;
                letter-spacing: 1px;
                }}
                .content {{
                padding: 20px;
                line-height: 1.6;
                color: #333333;
                }}
                .content p {{
                margin: 0 0 16px;
                }}
                .otp-code {{
                text-align: center;
                font-size: 24px;
                font-weight: bold;
                letter-spacing: 2px;
                color: #007BFF;
                margin: 20px 0;
                }}
                .footer {{
                background-color: #f1f1f1;
                padding: 10px;
                font-size: 12px;
                text-align: center;
                color: #777777;
                }}
                .link {{
                text-align: center;
                font-size: 16px;
                font-weight: bold;
                margin: 20px 0;
                }}
                .link a {{
                color: #007BFF;
                text-decoration: none;
                }}
            </style>
            </head>
            <body>
            <div class="container">
                <div class="header">
                <h1>MediPlus</h1>
                </div>
                <div class="content">
                <p>Bonjour,</p>
                <p>Merci d'avoir choisi MediPlus. Pour finaliser votre inscription, veuillez cliquer sur le lien ci-dessous et entrer le code OTP affiché pour vérifier votre compte :</p>
                <p class="link"><a href="{registration_link}">Compléter l'inscription</a></p>
                <p>Votre code OTP est :</p>
                <p class="otp-code">{otp}</p>
                <p>Si vous n’êtes pas à l’origine de cette demande, veuillez ignorer ce message.</p>
                <p>Nous vous souhaitons la bienvenue chez MediPlus.</p>
                </div>
                <div class="footer">
                <p>&copy; 2025 MediPlus. Tous droits réservés.</p>
                </div>
            </div>
            </body>
            </html>
            """

            # send_mail(
            #     'Complete Your Registration',
            #     f'Please complete your registration by visiting: {registration_link}. Use this OTP to verify: {otp}',
            #     'bahahembeirik@gmail.com',
            #     [email],
            #     fail_silently=False,
            # )

            # Generate a plain text version by stripping the HTML tags
            text_content = strip_tags(html_content)

            # Create the multi-part email message
            msg = EmailMultiAlternatives(
                subject,
                text_content,
                'bahahembeirik@gmail.com',  # Sender's email address
                [email],
            )

            # Attach the HTML alternative content
            msg.attach_alternative(html_content, "text/html")
            threading.Thread(target=lambda: msg.send(fail_silently=True), daemon=True).start()

            return Response({
                'message': 'Doctor created successfully. Registration link sent to email.',
                'registration_link': registration_link  # Include this in response for frontend redirection
            }, status=status.HTTP_201_CREATED)  
              
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request, doctor_id):
        """
        Update a doctor's hospital. Only Admin users can update, and only the 'hospital' field is updated.
        """
        if request.user.role != 'Admin':
            return Response({'error': 'Only Admin can update doctors'}, status=status.HTTP_403_FORBIDDEN)

        try:
            doctor = CustomUser.objects.get(id=doctor_id, role='Doctor')
        except CustomUser.DoesNotExist:
            return Response({'error': 'Doctor not found.'}, status=status.HTTP_404_NOT_FOUND)

        hospital_id = request.data.get('hospital')
        if not hospital_id:
            return Response({'error': 'Hospital field is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            hospital_obj = Hospital.objects.get(id=hospital_id)
        except Hospital.DoesNotExist:
            return Response({'error': 'Hospital not found.'}, status=status.HTTP_404_NOT_FOUND)

        doctor.hospital = hospital_obj
        doctor.save()
        return Response({'message': 'Doctor updated successfully.'}, status=status.HTTP_200_OK)
    
    def delete(self, request, doctor_id):
        """
        Delete a doctor. Only Admin users can delete a doctor.
        """
        if request.user.role != 'Admin':
            return Response({'error': 'Only Admin can delete doctors'}, status=status.HTTP_403_FORBIDDEN)

        try:
            doctor = CustomUser.objects.get(id=doctor_id, role='Doctor')
        except CustomUser.DoesNotExist:
            return Response({'error': 'Doctor not found.'}, status=status.HTTP_404_NOT_FOUND)

        doctor.delete()
        return Response({'message': 'Doctor deleted successfully.'}, status=status.HTTP_200_OK)


class PatientViewSet(viewsets.ModelViewSet):
    throttle_classes = [UserRateThrottle]

    permission_classes = [permissions.IsAuthenticated]
    queryset = Patient.objects.all()
    serializer_class = PatientSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['sex'] 
    search_fields = ['numero_identite','nom', 'prenom'] 


class DoctorListAPIView(APIView):
    throttle_classes = [UserRateThrottle]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        # Optional query parameter to filter by hospital
        hospital_id = request.query_params.get("hospital")
        
        if hospital_id:
            try:
                # Filter doctors by the provided hospital id and role "Doctor"
                doctors = CustomUser.objects.filter(hospital_id=hospital_id, role="Doctor")
            except Exception as e:
                return Response(
                    {"error": "Error fetching doctors for the specified hospital."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            # If no hospital_id is provided, fetch all doctors
            doctors = CustomUser.objects.filter(role="Doctor")
            
        serializer = DoctorSerializer(doctors, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)