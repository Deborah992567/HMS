import os
import logging

# --- Ensure logs folder exists ---
os.makedirs("logs", exist_ok=True)

# --- Logger configuration ---
logger = logging.getLogger("hms_logger")
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# File handler (logs/app.log)
fh = logging.FileHandler("logs/app.log")
fh.setFormatter(formatter)
logger.addHandler(fh)

# Console handler
ch = logging.StreamHandler()
ch.setFormatter(formatter)
logger.addHandler(ch)

# --- Logging function ---
def log_action(user_id: int, action: str):
    """
    Logs a user action with timestamp.
    """
    logger.info(f"User {user_id} performed action: {action}")
