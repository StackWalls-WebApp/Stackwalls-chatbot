from flask import Flask
from flask_cors import CORS
import os

# Import routes
from routes.project_discussion_routes import project_discussion_route
from routes.stackwalls_routes import stackwalls_route
from routes.cofounder_routes import cofounder_route
from routes.freelancer_routes import freelancer_route
from routes.youtube_routes import youtube_bp  # Interactive chat blueprint

app = Flask(__name__)
CORS(app)

# Ensure necessary directories exist for file uploads, PDF processing, etc.
os.makedirs('uploads', exist_ok=True)
os.makedirs('reports', exist_ok=True)

# Register the Blueprints for each "option" route
app.register_blueprint(project_discussion_route)
app.register_blueprint(stackwalls_route)
app.register_blueprint(cofounder_route)
app.register_blueprint(freelancer_route)
app.register_blueprint(youtube_bp)  # Register the interactive_chat blueprint



if __name__ == "__main__":
    # Run the Flask app on 0.0.0.0:5000. In production, set debug=False
    app.run(host='0.0.0.0', port=5000, debug=False)
