# Data Centre Ticketing System

A comprehensive Django-based ticketing system for data centre grey space management, built according to ITIL best practices. This full-grade enterprise ticketing system includes advanced features like SLA management, automated workflows, reporting, and comprehensive audit trails.

## 🚀 Features

### Core Ticketing Features
- **Ticket Management**: Create, update, assign, and track tickets with unique IDs
- **Priority & Status Management**: P1-P4 priority levels with customizable status workflows
- **Category & Subcategory System**: Organized ticket classification for better management
- **Asset Integration**: Link tickets to specific data centre assets (generators, AHUs, pumps, etc.)
- **Contact Management**: Track contact information for ticket requesters

### Advanced Features
- **SLA Management**: Automated SLA assignment based on priority with response/resolution time tracking
- **Comments & Communication**: Internal and external comments with notification system
- **File Attachments**: Upload and manage ticket-related documents and images
- **Audit Trail**: Complete history tracking of all ticket changes and activities
- **Time Tracking**: Estimated vs actual hours with productivity metrics
- **Bulk Operations**: Mass update, assign, or close multiple tickets

### User Management
- **Role-Based Access**: Technician, Engineer, Manager, BMS Staff, and Admin roles
- **Custom User Profiles**: Extended user information with department and contact details
- **Permission System**: Granular access control based on user roles

### Reporting & Analytics
- **Dashboard**: Real-time statistics and key performance indicators
- **Advanced Search**: Multi-criteria filtering and search capabilities
- **Reports**: Ticket volume, SLA performance, team productivity metrics
- **Visual Analytics**: Charts and graphs for trend analysis

### Knowledge Base
- **KB Articles**: Searchable knowledge base with categorized articles
- **Ticket Templates**: Pre-defined templates for common issues
- **Best Practices**: Integrated troubleshooting guides and procedures

## 🛠️ Technology Stack

- **Backend**: Django 5.2.5 with Python 3.13
- **Database**: SQLite (development) / PostgreSQL (production ready)
- **Frontend**: Tailwind CSS with responsive design
- **File Storage**: Django file handling with organized directory structure
- **Authentication**: Django's built-in authentication with custom user model

## 📋 Setup and Installation

### Prerequisites
- Python 3.11 or higher
- pip (Python package installer)
- Git

### Installation Steps

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd DjangoSiteBuilder-1.0.0
   ```

2. **Activate the virtual environment:**
   ```bash
   # For macOS/Linux
   source venv/bin/activate

   # For Windows
   .\venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run database migrations:**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

5. **Create sample data (recommended for testing):**
   ```bash
   python manage.py create_sample_data
   ```
   This creates:
   - Sample users with different roles
   - Ticket categories and subcategories
   - SLA definitions
   - Data centre assets
   - Sample tickets with various statuses
   - Knowledge base articles

6. **Create a superuser (optional - sample data includes admin user):**
   ```bash
   python manage.py createsuperuser
   ```

7. **Run the development server:**
   ```bash
   python manage.py runserver
   ```

8. **Access the application:**
   - Main application: `http://127.0.0.1:8000`
   - Admin interface: `http://127.0.0.1:8000/admin`

### Sample Login Credentials

After running `create_sample_data`, you can use these credentials:

- **Admin**: `admin` / `admin123`
- **Engineer**: `john.doe` / `password123`
- **Technician**: `jane.smith` / `password123`
- **Manager**: `mike.wilson` / `password123`
- **BMS Staff**: `sarah.jones` / `password123`

## 🎯 Usage Guide

### Dashboard
- View key metrics and statistics
- Quick access to recent tickets
- Priority and status distribution charts
- Overdue ticket alerts

### Ticket Management
1. **Create Ticket**: Use the "New Ticket" button to create tickets
2. **View Tickets**: Browse all tickets with advanced filtering
3. **Ticket Details**: View complete ticket information, comments, and attachments
4. **Update Tickets**: Edit ticket details, add comments, upload files
5. **Bulk Actions**: Select multiple tickets for mass operations

### Search & Filtering
- Search by ticket ID, title, or description
- Filter by status, priority, category, assignee
- Combine multiple filters for precise results

### Reports
- Access comprehensive reporting from the Reports menu
- View ticket volume trends
- Monitor SLA performance
- Analyze team productivity
- Export data for external analysis

## 🏗️ System Architecture

### Models
- **User**: Extended Django user with roles and contact info
- **Ticket**: Core ticket entity with comprehensive fields
- **TicketCategory/Subcategory**: Hierarchical classification
- **SLA**: Service Level Agreement definitions
- **Asset**: Data centre equipment and infrastructure
- **TicketComment**: Communication and updates
- **TicketAttachment**: File uploads and documents
- **TicketHistory**: Complete audit trail
- **KnowledgeBaseArticle**: Documentation and procedures

### Key Features Implementation
- **Automatic Ticket IDs**: Sequential ID generation (RX-UG-INC-XXXXXX)
- **SLA Monitoring**: Automatic SLA assignment and overdue detection
- **Audit Logging**: Comprehensive change tracking
- **File Management**: Organized file storage with size tracking
- **Responsive Design**: Mobile-friendly interface

## 🔧 Configuration

### Environment Settings
Key settings in `core/settings.py`:
- Database configuration
- Media file handling
- Authentication settings
- Debug mode

### Customization
- **Categories**: Add/modify ticket categories in admin
- **SLAs**: Configure response and resolution times
- **User Roles**: Extend or modify user role permissions
- **Templates**: Customize email and ticket templates

## 📊 Data Centre Specific Features

### Asset Types
- Generator Sets
- Air Handling Units (AHU)
- In-Row Air Conditioners
- Battery Banks
- GRP Tanks
- Pumps
- RO Plants
- Fire Suppression Systems

### Common Use Cases
- Equipment maintenance requests
- Environmental monitoring alerts
- Power system issues
- HVAC troubleshooting
- Fire safety system testing
- Water system maintenance
- Emergency response coordination

## 🚀 Production Deployment

### Database
- Configure PostgreSQL for production
- Set up database backups
- Configure connection pooling

### Security
- Change default secret key
- Configure HTTPS
- Set up proper authentication
- Configure file upload restrictions

### Performance
- Configure static file serving
- Set up caching
- Configure database indexing
- Monitor system performance

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Check the Knowledge Base articles in the application
- Review the admin documentation
- Contact the development team

---

**Built for Data Centre Operations Teams** 🏢⚡

This ticketing system is specifically designed for data centre grey space management, incorporating industry best practices and ITIL frameworks for efficient facility operations.