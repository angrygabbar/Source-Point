import cloudinary.uploader
from extensions import db
from models.hiring import JobOpening, JobApplication, CodeTestSubmission, CodeSnippet
from models.auth import User
from utils import send_email
from datetime import datetime

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
            return False, "Job not found."
            
        existing_application = JobApplication.query.filter_by(user_id=user.id, job_id=job.id).first()
        if existing_application:
            return False, "You have already applied for this job."

        # 2. Resume Upload (Cloudinary)
        resume_url = None
        if resume_file and resume_file.filename != '':
            if not resume_file.filename.endswith('.pdf'):
                return False, "Only PDF files are allowed."
            try:
                upload_result = cloudinary.uploader.upload(
                    resume_file, 
                    resource_type="raw", 
                    folder="application_resumes",
                    public_id=f"app_resume_{user.id}_{job.id}"
                )
                resume_url = upload_result['secure_url']
            except Exception as e:
                return False, f"Resume upload failed: {str(e)}"
        
        # Fallback to existing profile resume
        if not resume_url and user.resume_filename:
            resume_url = user.resume_filename

        if not resume_url:
            return False, "Please upload a resume to apply."

        # 3. Create Application Record
        try:
            new_application = JobApplication(user_id=user.id, job_id=job.id, resume_url=resume_url)
            db.session.add(new_application)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return False, "Database error while saving application."

        # 4. Notifications
        # Notify Admins & Recruiters
        admins = User.query.filter_by(role='admin').all()
        recruiters = User.query.filter_by(role='recruiter').all()
        recipient_emails = [u.email for u in admins + recruiters]
        
        if recipient_emails:
            admin_user = User.query.filter_by(role='admin').first()
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
        """
        if not recipient_id or not code.strip():
            return False, "Please select a recipient and provide code."
            
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
            return False, "Error saving submission."

        # Notification
        recipient = User.query.get(recipient_id)
        problem_title = candidate.assigned_problem.title if candidate.assigned_problem else "Unknown Problem"

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
            now=datetime.utcnow()
        )
        
        return True, "Your code test has been submitted successfully and sent via email!"

    @staticmethod
    def share_code_snippet(sender_id, recipient_id, code):
        if not recipient_id or not code or not code.strip():
            return False, "Please select a recipient and provide code."

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
            return False, "Error saving code snippet."
        
        return True, "Code snippet shared successfully!"