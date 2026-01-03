# 🔐 Secure Container Access Manager

A Python CLI tool to securely manage and audit Docker container access with authentication, role-based access control (RBAC), and session recording. 

## 📋 Overview

Secure Container Access Manager provides enterprise-grade security for Docker container access by implementing:
- **User Authentication**: Secure login with bcrypt password hashing
- **Role-Based Access Control (RBAC)**: Admin and user role management
- **Container Ownership**:  Automatic container claiming and ownership tracking
- **Session Recording**: Complete audit trail with typescript recording
- **Access Logging**: Comprehensive logs of all container access events

## ✨ Features

- 🔒 **Secure Authentication**: Password-based authentication with bcrypt hashing
- 👥 **User Management**: Admin and user roles with different permissions
- 🐳 **Container Access Control**: Validates container state before granting access
- 📝 **Session Recording**: Records all container sessions for audit purposes
- 🗄️ **SQLite Database**: Lightweight database for user, container, and log management
- 🔍 **Access Logs**: Track who accessed which containers and when
- ⚡ **Atomic Operations**: Transaction-based container claiming to prevent race conditions

## 🚀 Getting Started

### Prerequisites

- Python 3.7+
- Docker Engine installed and running
- Docker API accessible

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/MUHSIN-M-P/Secure-Container-Access-Manager.git
   cd Secure-Container-Access-Manager
   ```

2. **Install dependencies**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate # linux
   source .venv/scripts/activate #windows
   pip install -r requirements.txt
   ```

3. **Verify Docker connectivity**
   ```bash
   python src/check_docker.py
   ```

### Initial Setup

1. **Bootstrap the admin user**
   ```bash
   python src/bootstrap.py
   ```
   - Enter your desired admin username
   - Set a secure password (minimum 8 characters)
   - This creates the initial admin user and initializes the database

## 📖 Usage

### Database Schema

The system uses three main tables:

**Users Table**
- `id`: Primary key
- `username`: Unique username
- `password_hash`: Bcrypt hashed password
- `role`: Either 'admin' or 'user'
- `created_at`: Timestamp of user creation

**Containers Table**
- `id`: Primary key
- `container_name`: Unique container identifier
- `owner_username`: Username of the container owner

**Access Logs Table**
- `id`: Primary key
- `username`: User who accessed the container
- `container_name`: Container that was accessed
- `ts_start`: Session start timestamp
- `ts_end`: Session end timestamp
- `typescript_path`: Path to session recording file

### Authentication Flow

1. User runs the container access command
2. System prompts for username and password
3. Credentials are verified against the database
4. User role and permissions are retrieved

### Container Access Flow

1. System checks if Docker container exists and is running
2. Verifies or claims container ownership
3. Creates a session recording directory
4. Logs session start time
5. Grants access to the container
6. Records session end time

## 🗂️ Project Structure

```
Secure-Container-Access-Manager/
├── src/
│   ├── __main__.py          # Module entry point
│   ├── bootstrap.py         # Initial admin user setup
│   ├── check_docker.py      # Docker API connectivity check
│   ├── db.py                # Database initialization and connection
│   └── enter.py             # Container access and authentication logic
├── notes/                   # Project notes and documentation
├── requirements.txt         # Python dependencies
├── . gitignore              # Git ignore rules
└── README.md               # Project documentation
```

## 🛠️ Key Components

### Database Management (`db.py`)
- Initializes SQLite database at `~/.secure_container_access.db`
- Creates tables for users, containers, and access logs
- Provides connection management with proper timeouts

### Bootstrap (`bootstrap.py`)
- Creates the initial admin user
- Ensures only one admin can be created on first run
- Validates password strength (minimum 8 characters)

### Docker Validation (`check_docker.py`)
- Verifies Docker API accessibility
- Tests connection using Docker SDK

### Access Control (`enter.py`)
- User authentication with bcrypt
- Container state validation
- Ownership claiming with atomic transactions
- Session recording and logging

## 🔒 Security Features

- **Password Hashing**: Uses bcrypt with salt for secure password storage
- **Role-Based Access**:  Separate admin and user roles
- **Atomic Operations**: Prevents race conditions in container claiming
- **Session Recording**: Complete audit trail stored in `~/project/container_sessions/`
- **Restricted Permissions**: Session directories have 0o700 permissions
- **Database Constraints**: Enforces role values and foreign key relationships

