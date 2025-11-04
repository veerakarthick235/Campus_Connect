# CampusConnect Backend
 CampusConnect is a Flask-based backend system designed for managing campus internships,
 applications, and student-mentor-placement workflows efficiently. It includes authentication,
 email notifications, resume uploads, and recommendation features.
 ## 
 Features- JWT Authentication (Login, Register, Authorization)- Role-based Access (Student, Mentor, Placement Cell)- Internship Management (Create, View, Apply)- Application Workflow (Apply, Review, Schedule, Status Update)- Email Notifications (Application Status, Interview Schedule)- Resume Upload & Profile Update- AI-based Internship Recommendations- Analytics Dashboard (Company Engagement, Status Distribution)
 ## 
 Tech Stack- **Backend:** Flask (Python)- **Database:** MongoDB- **Authentication:** JWT- **Email Service:** Flask-Mail (SMTP)- **Password Hashing:** Bcrypt
 ## 
 Setup Instructions
 1. Clone the repository
   ```bash
   git clone <your-repo-url>
   cd backend
   ```
 2. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```
 3. Create a `.env` file with the following variables:
   ```env
   SECRET_KEY=your_secret_key
   MAIL_SERVER=smtp.gmail.com
   MAIL_PORT=587
   MAIL_USE_TLS=True
   MAIL_USERNAME=your_email@gmail.com
   MAIL_PASSWORD=your_email_password
   ```
 4. Run the Flask app
   ```bash
   python app.py
