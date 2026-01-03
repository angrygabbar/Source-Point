from extensions import db, bcrypt
from models.auth import User
from enums import UserRole
import sys

class AuthService:
    @staticmethod
    def register_user(username, email, password, role, mobile_number=None):
        # 1. Validation: Check duplicates
        if User.query.filter((User.email == email) | (User.username == username)).first():
            return None, "Username or email already exists."

        # 2. Security: Hash Password
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        
        # 3. Logic: Generate Avatar
        avatar_url = f'https://api.dicebear.com/8.x/initials/svg?seed={username}'

        # 4. Create User Instance
        new_user = User(
            username=username, 
            email=email, 
            password_hash=hashed_password, 
            role=role, 
            avatar_url=avatar_url, 
            mobile_number=mobile_number
        )

        # 5. Business Rule: First user is always Admin & Approved
        try:
            if User.query.count() == 0:
                new_user.role = UserRole.ADMIN.value
                new_user.is_approved = True
        except Exception as e:
            print(f"DEBUG: Error checking user count: {e}", file=sys.stderr)

        # 6. Persistence: Save to DB
        try:
            db.session.add(new_user)
            db.session.commit()
            return new_user, "Account created successfully! Please wait for admin approval."
        except Exception as e:
            db.session.rollback()
            print(f"Registration Error: {e}", file=sys.stderr)
            return None, "An error occurred during registration."

    @staticmethod
    def authenticate_user(email, password):
        """
        Verifies credentials and account status.
        """
        print(f"DEBUG: Attempting to find user with email: {email}", file=sys.stderr)
        
        try:
            user = User.query.filter_by(email=email).first()
        except Exception as e:
            print(f"DEBUG: Database connection error occurred: {e}", file=sys.stderr)
            return None, "System error connecting to database."

        if not user:
            print("DEBUG: User not found in database.", file=sys.stderr)
            return None, "Login failed. Please check your email and password."
        
        print(f"DEBUG: User found (ID: {user.id}, Role: {user.role}). Checking password...", file=sys.stderr)

        if not bcrypt.check_password_hash(user.password_hash, password):
            print("DEBUG: Password hash verification failed.", file=sys.stderr)
            return None, "Login failed. Please check your email and password."
        
        # 2. Verify Status
        if not user.is_approved:
            print("DEBUG: User account is not approved.", file=sys.stderr)
            return None, "Your account has not been approved by an administrator yet."
        
        if not user.is_active:
            print("DEBUG: User account is inactive/blocked.", file=sys.stderr)
            return None, "Your account is blocked by admin. Kindly contact support."
            
        print("DEBUG: Authentication successful.", file=sys.stderr)
        return user, "Success"