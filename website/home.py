from flask import Blueprint, render_template

# Register Flask blueprint
home = Blueprint('home', __name__)

# Home page Flask route
@home.route('/')
def home_page():
    """

    This function renders the home page of the website using the 'home.html' template.
    Users accessing the root URL '/' will be directed to this page.

    Returns:
    HTML: Rendered HTML template for the home page.
    """
    return render_template('home.html')
