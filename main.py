from website import create_app

# Creation of Flask app / SQLite database
app = create_app()

if __name__ == '__main__':
    # Run Flask application
    app.run(debug=True)
