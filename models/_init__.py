from .auth import User, Message, ActivityUpdate, ActivityLog, candidate_contacts
from .commerce import (Product, ProductImage, Order, OrderItem, Cart, CartItem,
                       Invoice, InvoiceItem, StockRequest, SellerInventory, AffiliateAd)
from .hiring import (JobOpening, JobApplication, CodeTestSubmission, CodeSnippet,
                     Feedback, ModeratorAssignmentHistory)
from .learning import LearningContent, ProblemStatement
# REMOVED EMIPayment from this line:
from .finance import Project, Transaction, BRD, EMIPlan
from .interview import Interview, InterviewParticipant, InterviewFeedback
from .mcq import MCQQuestion, Test, TestAssignment, TestResult
#from .payment import EMIPayment