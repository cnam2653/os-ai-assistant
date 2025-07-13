import logging
from livekit.agents import function_tool, RunContext
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional
import subprocess
import psutil

@function_tool()
async def send_email(
    context: RunContext,  # type: ignore
    to_email: str,
    subject: str,
    message: str,
    cc_email: Optional[str] = None
) -> str:
    """
    Send an email through Gmail.
    
    Args:
        to_email: Recipient email address
        subject: Email subject line
        message: Email body content
        cc_email: Optional CC email address
    """
    try:
        # Gmail SMTP configuration
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        
        # Get credentials from environment variables
        gmail_user = os.getenv("GMAIL_USER")
        gmail_password = os.getenv("GMAIL_APP_PASSWORD")  # Use App Password, not regular password
        
        if not gmail_user or not gmail_password:
            logging.error("Gmail credentials not found in environment variables")
            return "Email sending failed: Gmail credentials not configured."
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = gmail_user
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # Add CC if provided
        recipients = [to_email]
        if cc_email:
            msg['Cc'] = cc_email
            recipients.append(cc_email)
        
        # Attach message body
        msg.attach(MIMEText(message, 'plain'))
        
        # Connect to Gmail SMTP server
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()  # Enable TLS encryption
        server.login(gmail_user, gmail_password)
        
        # Send email
        text = msg.as_string()
        server.sendmail(gmail_user, recipients, text)
        server.quit()
        
        logging.info(f"Email sent successfully to {to_email}")
        return f"Email sent successfully to {to_email}"
        
    except smtplib.SMTPAuthenticationError:
        logging.error("Gmail authentication failed")
        return "Email sending failed: Authentication error. Please check your Gmail credentials."
    except smtplib.SMTPException as e:
        logging.error(f"SMTP error occurred: {e}")
        return f"Email sending failed: SMTP error - {str(e)}"
    except Exception as e:
        logging.error(f"Error sending email: {e}")
        return f"An error occurred while sending email: {str(e)}"

@function_tool()
async def open_file(
    context: RunContext,  # type: ignore
    file_path: str) -> str:
    """
    Open a file or folder using the default Windows application.
    
    Args:
        file_path: Full path to the file or folder to open
    """
    try:
        # Normalize the path and handle Windows path formats
        file_path = os.path.normpath(file_path)
        
        # Check if path exists
        if not os.path.exists(file_path):
            logging.error(f"File or folder not found: {file_path}")
            return f"File or folder not found: {file_path}"
        
        # Open file/folder with default Windows application
        os.startfile(file_path)
        
        file_type = "folder" if os.path.isdir(file_path) else "file"
        logging.info(f"Successfully opened {file_type}: {file_path}")
        return f"Successfully opened {file_type}: {os.path.basename(file_path)}"
        
    except Exception as e:
        logging.error(f"Error opening file {file_path}: {e}")
        return f"An error occurred while opening {file_path}: {str(e)}"

@function_tool()
async def open_application(
    context: RunContext,  # type: ignore
    app_name: str) -> str:
    """
    Open an application by name on Windows using direct paths for faster execution.
    
    Args:
        app_name: Name of the application to open
    """
    
    # Direct path mappings 
    app_mappings = {
        # Browsers 
        "chrome": [r"C:\Program Files\Google\Chrome\Application\chrome.exe"],
        "google chrome": [r"C:\Program Files\Google\Chrome\Application\chrome.exe"],
        
        # Communication 
        "discord": [r"C:\Users\Chris\AppData\Local\Discord\app-1.0.9198\Discord.exe"],
        
        # Gaming - Update these paths
        "steam": [r"C:\Program Files (x86)\Steam\Steam.exe"],
        "valorant": [r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs\Riot Games\VALORANT.lnk"],
        
        # Media - Update these paths
        "spotify": [r"C:\Users\Chris\AppData\Roaming\Spotify\Spotify.exe"],
        "medal": [r"C:\Users\Chris\AppData\Local\Medal\app-4.2746.0\Medal.exe"],
        
        # Development - Update with your VS Code path
        "vscode": [r"C:\Users\Chris\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Visual Studio Code\Visual Studio Code.lnk"],
        "visual studio code": [r"C:\Users\Chris\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Visual Studio Code\Visual Studio Code.lnk"],
        
        # System apps 
        "powershell": [r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"],
        "cmd": [r"C:\Windows\System32\cmd.exe"],
        "command prompt": [r"C:\Windows\System32\cmd.exe"],
        "task manager": [r"C:\Windows\System32\taskmgr.exe"],
        "settings": ["ms-settings:"],  # This one uses protocol handler
        "notepad": [r"C:\Windows\System32\notepad.exe"],
        "paint": [r"C:\Windows\System32\mspaint.exe"],
        "explorer": [r"C:\Windows\explorer.exe"],
        "file explorer": [r"C:\Windows\explorer.exe"],
        
        # Special cases
        "google meet": [r"C:\Program Files\Google\Chrome\Application\chrome.exe", "https://meet.google.com"],
    }
    
    app_name_lower = app_name.lower()
    
    if app_name_lower not in app_mappings:
        logging.warning(f"Application '{app_name}' is not in the allowed list")
        return f"Sorry, I can only open these applications: {', '.join(app_mappings.keys())}"
    
    try:
        # Check if application is already running
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if app_name_lower in proc.info['name'].lower():
                    logging.info(f"{app_name} is already running (PID: {proc.info['pid']})")
                    return f"{app_name} is already running."
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        # Get the path(s) for the application
        paths = app_mappings[app_name_lower]
        
        # Special handling for Google Meet
        if app_name_lower == "google meet":
            chrome_path = paths[0]
            url = paths[1]
            if os.path.exists(chrome_path):
                subprocess.Popen([chrome_path, url])
                logging.info(f"Successfully opened Google Meet in Chrome")
                return f"Successfully opened Google Meet in Chrome"
            else:
                return f"Chrome not found at {chrome_path}"
        
        # Try each path until one works
        for path in paths:
            try:
                logging.debug(f"Trying path: {path}")

                if path.startswith("ms-settings:"):
                    subprocess.run(["start", path], shell=True, check=True)
                    logging.info(f"Successfully opened {app_name}")
                    return f"Successfully opened {app_name}"

                if "--" in path:
                    exe_path, args_str = path.split(" --", 1)
                    exe_path = exe_path.strip()
                    args = ["--" + arg.strip() for arg in args_str.split("--") if arg.strip()]
                else:
                    exe_path = path
                    args = []

                logging.debug(f"Checking if executable exists: {exe_path}")
                if os.path.exists(exe_path):
                    logging.debug(f"Executable found: {exe_path}")
                    if args:
                        subprocess.Popen([exe_path] + args)
                    else:
                        subprocess.Popen([exe_path])

                    logging.info(f"Successfully opened {app_name}")
                    return f"Successfully opened {app_name}"
                else:
                    logging.warning(f"Path does not exist or is invalid: {exe_path}")
                    continue

            except Exception as e:
                logging.error(f"Failed to open {path}: {e}")
                continue

        return f"Could not find or open {app_name}"

    except Exception as e:
        logging.error(f"Error opening {app_name}: {e}")
        return f"An error occurred while trying to open {app_name}: {str(e)}"

@function_tool()
async def find_app_paths(
    context: RunContext,  # type: ignore
    app_name: str) -> str:
    """
    Helper function to find the actual installation paths for applications.
    Use this to discover the correct paths for your system.
    """
    try:
        found_paths = []
        
        # Common installation directories
        search_paths = [
            os.path.expandvars(r"%ProgramFiles%"),
            os.path.expandvars(r"%ProgramFiles(x86)%"),
            os.path.expandvars(r"%LocalAppData%\Programs"),
            os.path.expandvars(r"%AppData%\Local"),
            os.path.expandvars(r"%AppData%\Roaming"),
        ]
        
        app_name_lower = app_name.lower()
        
        for base_path in search_paths:
            if os.path.exists(base_path):
                for root, dirs, files in os.walk(base_path):
                    # Look for executable files
                    for file in files:
                        if file.lower().endswith('.exe') and app_name_lower in file.lower():
                            full_path = os.path.join(root, file)
                            found_paths.append(full_path)
                    
                    # Also look for folders with the app name
                    for dir_name in dirs:
                        if app_name_lower in dir_name.lower():
                            # Look for exe files in this directory
                            app_dir = os.path.join(root, dir_name)
                            try:
                                for file in os.listdir(app_dir):
                                    if file.lower().endswith('.exe'):
                                        full_path = os.path.join(app_dir, file)
                                        found_paths.append(full_path)
                            except (PermissionError, OSError):
                                continue
                    
                    # Limit search depth to avoid taking too long
                    if len(root.split(os.sep)) - len(base_path.split(os.sep)) > 3:
                        dirs[:] = []
        
        if found_paths:
            # Remove duplicates and limit results
            unique_paths = list(dict.fromkeys(found_paths))[:10]
            return f"Found {app_name} at these locations:\n" + "\n".join(unique_paths)
        else:
            return f"Could not find {app_name} in common installation directories."
            
    except Exception as e:
        logging.error(f"Error finding {app_name}: {e}")
        return f"An error occurred while searching for {app_name}: {str(e)}"

@function_tool()
async def close_application(
    context: RunContext,  # type: ignore
    application_name: str
) -> str:
    """
    Close an application by name on Windows with better process targeting.
    
    Args:
        application_name: Name of the application to close (e.g., "steam", "chrome", "notepad")
    """
    app_name_lower = application_name.lower()
    closed_processes = []
    
    # More specific process name mappings for better targeting
    process_mappings = {
        "chrome": ["chrome.exe"],
        "google chrome": ["chrome.exe"],
        "discord": ["Discord.exe"],
        "steam": ["steam.exe"],
        "valorant": ["VALORANT.exe", "RiotClientServices.exe"],
        "spotify": ["Spotify.exe"],
        "medal": ["Medal.exe"],
        "vscode": ["Code.exe"],
        "visual studio code": ["Code.exe"],
        "powershell": ["powershell.exe"],
        "cmd": ["cmd.exe"],
        "command prompt": ["cmd.exe"],
        "task manager": ["taskmgr.exe"],
        "calculator": ["calc.exe"],
        "notepad": ["notepad.exe"],
        "explorer": ["explorer.exe"],
        "file explorer": ["explorer.exe"],
    }
    
    try:
        # Get the specific process names to look for
        if app_name_lower in process_mappings:
            target_processes = process_mappings[app_name_lower]
        else:
            # Fallback to generic matching
            target_processes = [f"{app_name_lower}.exe"]
        
        # Find and terminate processes matching the specific process names
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                proc_name = proc.info['name'].lower()
                if any(target.lower() == proc_name for target in target_processes):
                    proc.terminate()
                    closed_processes.append(f"{proc.info['name']} (PID: {proc.info['pid']})")
                    logging.info(f"Terminated {proc.info['name']} (PID: {proc.info['pid']})")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        if closed_processes:
            return f"Successfully closed {application_name}: {', '.join(closed_processes)}"
        else:
            return f"{application_name} is not currently running."
            
    except Exception as e:
        logging.error(f"Error closing {application_name}: {e}")
        return f"An error occurred while trying to close {application_name}: {str(e)}"


@function_tool()
async def run_command(
    context: RunContext,  # type: ignore
    command: str) -> str:
    """
    Run a Windows command line command.
    
    Args:
        command: The command to execute
    """
    try:
        # Run the command and capture output
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30  # 30 second timeout
        )
        
        output = result.stdout.strip()
        error = result.stderr.strip()
        
        if result.returncode == 0:
            logging.info(f"Command '{command}' executed successfully")
            return f"Command executed successfully:\n{output}" if output else "Command executed successfully (no output)"
        else:
            logging.error(f"Command '{command}' failed with return code {result.returncode}")
            return f"Command failed with return code {result.returncode}:\n{error}" if error else f"Command failed with return code {result.returncode}"
            
    except subprocess.TimeoutExpired:
        logging.error(f"Command '{command}' timed out")
        return f"Command timed out after 30 seconds"
    except Exception as e:
        logging.error(f"Error running command '{command}': {e}")
        return f"An error occurred while running the command: {str(e)}"