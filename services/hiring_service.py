import cloudinary.uploader
import os
from io import BytesIO
from pypdf import PdfReader
# --- NEW SDK IMPORT ---
import google.generativeai as genai  # <--- THIS IS CORRECT
# ----------------------
from extensions import db
from models.hiring import JobOpening, JobApplication, CodeTestSubmission, CodeSnippet
from models.auth import User
from utils import send_email
from datetime import datetime
from errors import BusinessValidationError, ResourceNotFoundError
from enums import UserRole

class HiringService:
    @staticmethod
    def apply_for_job(user, job_id, resume_file):
        """
        Handles job application process including resume upload and notifications.
        Returns: (Success Boolean, Message String)
        """
        # 1. Validation
        job = JobOpening.query.get(job_id)
        if not job:
            raise ResourceNotFoundError("Job", job_id)
            
        existing_application = JobApplication.query.filter_by(user_id=user.id, job_id=job.id).first()
        if existing_application:
            raise BusinessValidationError("You have already applied for this job.")

        # 2. Resume Upload (Cloudinary)
        resume_url = None
        if resume_file and resume_file.filename != '':
            # --- SECURITY ENHANCEMENT: Validate PDF Content ---
            try:
                # Read file into memory to validate
                file_content = resume_file.read()
                file_stream = BytesIO(file_content)
                
                # Try to read the PDF structure
                reader = PdfReader(file_stream)
                if len(reader.pages) == 0:
                    raise BusinessValidationError("Uploaded PDF is empty.")
                    
                # IMPORTANT: Reset pointer for Cloudinary upload
                resume_file.seek(0) 
            except Exception as e:
                print(f"PDF Validation Error: {e}")
                raise BusinessValidationError("Invalid file format. Please upload a valid PDF.")
            # --------------------------------------------------

            try:
                upload_result = cloudinary.uploader.upload(
                    resume_file, 
                    resource_type="raw", 
                    folder="application_resumes",
                    public_id=f"app_resume_{user.id}_{job.id}"
                )
                resume_url = upload_result['secure_url']
            except Exception as e:
                print(f"Upload failed: {e}")
                raise BusinessValidationError("Failed to upload resume. Please try again.")
        
        # Fallback to existing profile resume
        if not resume_url and user.resume_filename:
            resume_url = user.resume_filename

        if not resume_url:
            raise BusinessValidationError("Please upload a resume to apply.")

        # 3. Create Application Record
        try:
            new_application = JobApplication(user_id=user.id, job_id=job.id, resume_url=resume_url)
            db.session.add(new_application)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise Exception(f"Database error: {e}")

        # 4. Notifications
        # Use Enums for role lookup
        admins = User.query.filter_by(role=UserRole.ADMIN.value).all()
        recruiters = User.query.filter_by(role=UserRole.RECRUITER.value).all()
        recipient_emails = [u.email for u in admins + recruiters]
        
        if recipient_emails:
            admin_user = User.query.filter_by(role=UserRole.ADMIN.value).first()
            send_email(
                to=recipient_emails, 
                subject=f"New Job Application: {job.title}", 
                template="mail/application_submitted_admin.html", 
                admin=admin_user, 
                candidate=user, 
                job=job, 
                now=datetime.utcnow()
            )
        
        # Notify Candidate
        send_email(
            to=user.email, 
            subject=f"Application Received: {job.title}", 
            template="mail/application_submitted_candidate.html", 
            candidate=user, 
            job=job, 
            now=datetime.utcnow()
        )

        return True, "You have successfully applied for the job!"

    @staticmethod
    def submit_code_test(candidate, recipient_id, code, output):
        """
        Handles code test submission and email notification.
        ENHANCEMENT: Uses new Google Gen AI SDK.
        """
        if not recipient_id or not code.strip():
            raise BusinessValidationError("Please select a recipient and provide code.")
            
        # --- AI ENHANCEMENT: Automated Grading (google-genai) ---
        ai_feedback = "AI Grading unavailable."
        
        if os.environ.get('GEMINI_API_KEY'):
            try:
                # Initialize Client (New SDK pattern)
                client = genai.Client(api_key=os.environ.get('GEMINI_API_KEY'))
                
                prompt = (
                    f"Analyze the following Java code submitted for a test.\n"
                    f"Code:\n{code}\n\n"
                    f"Output produced:\n{output}\n\n"
                    f"Provide a brief summary of code correctness, time complexity, "
                    f"and any potential bugs. Keep it under 150 words."
                )
                
                # Call the model
                response = client.models.generate_content(
                    model='gemini-1.5-flash', 
                    contents=prompt
                )
                
                if response.text:
                    ai_feedback = response.text
                else:
                    ai_feedback = "AI could not generate a response."
                    
            except Exception as e:
                print(f"Gemini API Error: {e}")
                ai_feedback = f"AI Analysis Failed (Service Error)."
        # -----------------------------------------

        try:
            submission = CodeTestSubmission(
                candidate_id=candidate.id, 
                recipient_id=recipient_id, 
                code=code, 
                output=output, 
                language='java'
            )
            db.session.add(submission)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"DB Error: {e}")
            raise Exception("Error saving submission.")

        # Notification
        recipient = User.query.get(recipient_id)
        if not recipient:
             raise ResourceNotFoundError("Recipient", recipient_id)
             
        # Check if the candidate has a problem assigned
        problem_title = "General Assessment"
        if hasattr(candidate, 'assigned_problem') and candidate.assigned_problem:
             problem_title = candidate.assigned_problem.title

        send_email(
            to=recipient.email, 
            cc=[candidate.email], 
            subject=f"New Code Submission from {candidate.username}",
            template="mail/submit_code_test.html", 
            candidate=candidate, 
            recipient=recipient,
            problem_title=problem_title, 
            language='java', 
            code=code, 
            output=output,
            ai_feedback=ai_feedback,
            now=datetime.utcnow()
        )
        
        return True, "Your code test has been submitted successfully and sent via email!"

    @staticmethod
    def share_code_snippet(sender_id, recipient_id, code):
        if not recipient_id or not code or not code.strip():
            raise BusinessValidationError("Please select a recipient and provide code.")

        try:
            new_snippet = CodeSnippet(
                sender_id=sender_id, 
                recipient_id=recipient_id, 
                code=code, 
                language='java'
            )
            db.session.add(new_snippet)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise Exception("Error saving code snippet.")
        
        return True, "Code snippet shared successfully!"