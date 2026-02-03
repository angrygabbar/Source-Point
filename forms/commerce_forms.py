from flask_wtf import FlaskForm
from wtforms import TextAreaField, BooleanField
from wtforms.validators import DataRequired, Length

class CheckoutForm(FlaskForm):
    shipping_address = TextAreaField(
        'Shipping Address', 
        validators=[
            DataRequired(message="Shipping address is required."),
            Length(min=10, max=500, message="Address must be between 10 and 500 characters.")
        ]
    )
    
    billing_address = TextAreaField(
        'Billing Address', 
        validators=[
            DataRequired(message="Billing address is required."),
            Length(min=10, max=500, message="Address must be between 10 and 500 characters.")
        ]
    )
    
    same_as_shipping = BooleanField('Same as shipping')