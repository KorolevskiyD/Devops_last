import logging
import re
from dotenv import load_dotenv
import os
import paramiko


from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler,CallbackContext

import psycopg2
from psycopg2 import sql


load_dotenv()

TOKEN = os.getenv("TOKEN")
#print(TOKEN)
SSH_HOST = os.getenv("RM_HOST")
SSH_PORT = os.getenv("RM_PORT")
SSH_USER = os.getenv("RM_USER")
SSH_PASSWORD = os.getenv("RM_PASSWORD")

SSH_HOST_DEB = os.getenv("RM_HOST_DEB")
SSH_PORT_DEB = os.getenv("RM_PORT_DEB")
SSH_USER_DEB = os.getenv("RM_USER_DEB")
SSH_PASSWORD_DEB = os.getenv("RM_PASSWORD_DEB")

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_DATABASE")

REMOTE_REPLICATION_LOG_PATH = '/var/log/postgresql/postgresql-15-main.log'

logging.basicConfig(
    filename='logfile.txt', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

FIND_PHONE_NUMBER, FIND_EMAIL, VERIFY_PASSWORD = range(3)
FIND_PHONE_NUMBER_CONFIRMATION, FIND_EMAIL_CONFIRMATION = range(3, 5)


def start(update: Update, context):
    user = update.effective_user
    update.message.reply_text(f'Hello, {user.full_name}!')

def helpCommand(update: Update, context):
    update.message.reply_text('This bot can help you find phone numbers and email addresses from text and verify password. Use /find_phone_number or /find_email, or /verify_password')

def findPhoneNumbersCommand(update: Update, context):
    update.message.reply_text('Please enter the text to search for phone numbers: ')
    return FIND_PHONE_NUMBER

def findEmailCommand(update: Update, context):
    update.message.reply_text('Please enter the text to search for email addresses: ')
    return FIND_EMAIL

def verifyPasswordCommand(update: Update, context):
    update.message.reply_text('Please enter the password to verify: ')
    return VERIFY_PASSWORD

def findPhoneNumbers(update: Update, context):
    user_input = update.message.text  

    #phoneNumRegex = re.compile(r'8 \(\d{3}\) \d{3}-\d{2}-\d{2}')
    phoneNumRegex = re.compile(
        r'(?:\+7|8)'           #  '+7' или '8' в начале
        r'[\s\-]?'             # Необязательный пробел
        r'\(?\d{3}\)?'         # 3 цифры с необяз. скобками
        r'[\s\-]?'             # Необязательный пробел
        r'\d{3}'               # Первый блок из трёх цифр
        r'[\s\-]?'             # Необяз. пробел или тире
        r'\d{2}'               # Блок из 2 цифр
        r'[\s\-]?\d{2}'        # Последний блок из 2 цифр с необяз. пробелом или тире
    )
    
    phoneNumberList = phoneNumRegex.findall(user_input)

    if not phoneNumberList:
        update.message.reply_text('No phone numbers found.')
        return ConversationHandler.END

    phoneNumbers = '\n'.join([f'{i+1}. {num}' for i, num in enumerate(phoneNumberList)])
    update.message.reply_text(f'Found phone numbers:\n{phoneNumbers}\n\nWould you like to save them to the database? (yes/no)')

    context.user_data['phone_numbers'] = phoneNumberList  
    return FIND_PHONE_NUMBER_CONFIRMATION  

def findEmails(update: Update, context):
    user_input = update.message.text

    emailRegex = re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+')

    emailList = emailRegex.findall(user_input)

    if not emailList:
        update.message.reply_text('No email addresses found.')
        return ConversationHandler.END

    emails = '\n'.join([f'{i+1}. {email}' for i, email in enumerate(emailList)])
    update.message.reply_text(f'Found email addresses:\n{emails}\n\nWould you like to save them to the database? (yes/no)')

    context.user_data['emails'] = emailList  
    return FIND_EMAIL_CONFIRMATION

def verifyPassword(update: Update, context):
    password = update.message.text  
    password_regex = re.compile(
        r'^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[!@#$%^&*()])[A-Za-z\d!@#$%^&*()]{8,}$'
    )

    if password_regex.match(password):
        update.message.reply_text('Password is complex.')
    else:
        update.message.reply_text('Password is simple.')

    return ConversationHandler.END

def ssh_connect(command):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SSH_HOST, port=SSH_PORT, username=SSH_USER, password=SSH_PASSWORD)

    stdin, stdout, stderr = ssh.exec_command(command)
    result = stdout.read().decode('utf-8')
    ssh.close()
    return result

def get_release(update: Update, context):
    result = ssh_connect("lsb_release -a")
    update.message.reply_text(f"System Release Information:\n{result}")

def get_uname(update: Update, context):
    result = ssh_connect("uname -a")
    update.message.reply_text(f"System Info:\n{result}")

def get_uptime(update: Update, context):
    result = ssh_connect("uptime")
    update.message.reply_text(f"System Uptime:\n{result}")

def get_df(update: Update, context):
    result = ssh_connect("df -h")
    update.message.reply_text(f"Filesystem Status:\n{result}")

def get_free(update: Update, context):
    result = ssh_connect("free -h")
    update.message.reply_text(f"Memory Status:\n{result}")

def get_mpstat(update: Update, context):
    result = ssh_connect("mpstat -P ALL")
    update.message.reply_text(f"CPU Performance Stats:\n{result}")

def get_w(update: Update, context):
    result = ssh_connect("w")
    update.message.reply_text(f"Logged in Users:\n{result}")

def get_auths(update: Update, context):
    result = ssh_connect("last -n 10")
    update.message.reply_text(f"Last 10 Login Attempts:\n{result}")

def get_critical(update: Update, context):
    result = ssh_connect("grep 'CRITICAL' /var/log/syslog | tail -n 5")
    update.message.reply_text(f"Last 5 Critical Logs:\n{result}")

def get_ps(update: Update, context):
    result = ssh_connect("ps aux")
    update.message.reply_text(f"Running Processes:\n{result}")

def get_ss(update: Update, context):
    result = ssh_connect("ss -tuln")
    update.message.reply_text(f"Used Ports:\n{result}")

def get_apt_list(update: Update, context):
    result = ssh_connect("apt list --installed")
    update.message.reply_text(f"Installed Packages:\n{result[:4000]}")

def search_package(update: Update, context):
    package_name = update.message.text.split()[-1]
    result = ssh_connect(f"apt list --installed | grep {package_name}")
    if result:
        update.message.reply_text(f"Package Information:\n{result}")
    else:
        update.message.reply_text(f"No such package: {package_name}")

def get_services(update: Update, context):
    result = ssh_connect("systemctl list-units --type=service --state=running")
    update.message.reply_text(f"Running Services:\n{result}")


def ssh_connect_deb(command):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SSH_HOST_DEB, port=SSH_PORT_DEB, username=SSH_USER_DEB, password=SSH_PASSWORD_DEB)

    stdin, stdout, stderr = ssh.exec_command(command)
    result = stdout.read().decode('utf-8')
    ssh.close()
    return result

def get_repl_logs(update: Update, context: CallbackContext):
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SSH_HOST_DEB, port=SSH_PORT_DEB, username=SSH_USER_DEB, password=SSH_PASSWORD_DEB)

        command = f"tail -n 20 {REMOTE_REPLICATION_LOG_PATH} "   
        
        stdin, stdout, stderr = ssh.exec_command(command)

        logs = stdout.read().decode('utf-8')
        error = stderr.read().decode('utf-8')

        logger.info(f"Logs: {logs}")
        logger.info(f"Error: {error}")

        if error:
            update.message.reply_text(f"Error fetching logs: {error}")
        elif logs.strip():
            update.message.reply_text(f"Last 20 lines of the replication log:\n\n{logs}")
        else:
            update.message.reply_text("No recent replication logs found.")
    except Exception as e:
        logger.error(f"Error executing remote command: {e}")
        update.message.reply_text("An error occurred while fetching the logs.")
    finally:
        ssh.close()


def connect_db():
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        return conn
    except Exception as e:
        logger.error(f"Error connecting to the database: {e}")
        return None

def fetch_emails():
    conn = connect_db()
    if not conn:
        return "Failed to connect to the database."

    try:
        with conn.cursor() as cursor:
            query = sql.SQL("SELECT address FROM email_addresses WHERE email_addresses IS NOT NULL")
            cursor.execute(query)
            emails = cursor.fetchall()
            
            if emails:
                email_list = "\n".join([str(email[0]) for email in emails])
                return f"Email addresses:\n{email_list}"
            else:
                return "No email addresses found."
    except Exception as e:
        logger.error(f"Error fetching emails: {e}")
        return "Error fetching email addresses."
    finally:
        conn.close()


def fetch_phone_numbers():
    conn = connect_db()
    if not conn:
        return "Failed to connect to the database."

    try:
        with conn.cursor() as cursor:
            query = sql.SQL("SELECT number FROM phone_numbers WHERE phone_numbers IS NOT NULL")
            cursor.execute(query)
            phone_numbers = cursor.fetchall()
            
            if phone_numbers:
                phone_list = "\n".join([str(phone[0]) for phone in phone_numbers])
                return f"Phone numbers:\n{phone_list}"
            else:
                return "No phone numbers found."
    except Exception as e:
        logger.error(f"Error fetching phone numbers: {e}")
        return "Error fetching phone numbers."
    finally:
        conn.close()

        
def get_emails(update: Update, context: CallbackContext):
    emails = fetch_emails()
    update.message.reply_text(emails)

def get_phone_numbers(update: Update, context: CallbackContext):
    phone_numbers = fetch_phone_numbers()
    update.message.reply_text(phone_numbers)

def echo(update: Update, context):
    update.message.reply_text('Please use one of the following commands: /find_phone_number, /find_email or /verify_password.')

def confirmPhoneNumbers(update: Update, context: CallbackContext):
    response = update.message.text.lower()

    if response == 'yes':
        phoneNumbers = context.user_data.get('phone_numbers', [])
        if phoneNumbers:
            result = savePhoneNumbers(phoneNumbers)
            if result:
                update.message.reply_text('Phone numbers saved successfully.')
            else:
                update.message.reply_text('Error saving phone numbers.')
        else:
            update.message.reply_text('No phone numbers to save.')
    else:
        update.message.reply_text('Operation cancelled.')

    return ConversationHandler.END


def confirmEmails(update: Update, context: CallbackContext):
    response = update.message.text.lower()

    if response == 'yes':
        emails = context.user_data.get('emails', [])
        if emails:
            result = saveEmails(emails)
            if result:
                update.message.reply_text('Email addresses saved successfully.')
            else:
                update.message.reply_text('Error saving email addresses.')
        else:
            update.message.reply_text('No email addresses to save.')
    else:
        update.message.reply_text('Operation cancelled.')

    return ConversationHandler.END


def savePhoneNumbers(phoneNumbers):
    conn = connect_db()
    if not conn:
        return False

    try:
        with conn.cursor() as cursor:
            for phone in phoneNumbers:
                query = sql.SQL("INSERT INTO phone_numbers (number) VALUES (%s)")
                cursor.execute(query, (phone,))
            conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error saving phone numbers: {e}")
        return False
    finally:
        conn.close()


def saveEmails(emails):
    conn = connect_db()
    if not conn:
        return False

    try:
        with conn.cursor() as cursor:
            for email in emails:
                query = sql.SQL("INSERT INTO email_addresses (address) VALUES (%s)")
                cursor.execute(query, (email,))
            conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error saving email addresses: {e}")
        return False
    finally:
        conn.close()

def main():
    updater = Updater(TOKEN, use_context=True)

    dp = updater.dispatcher


    convHandlerFindPhoneNumbers = ConversationHandler(
        entry_points=[CommandHandler('find_phone_number', findPhoneNumbersCommand)],
        states={
            FIND_PHONE_NUMBER: [MessageHandler(Filters.text & ~Filters.command, findPhoneNumbers)],
        },
        fallbacks=[]
    )

    convHandlerFindPhoneNumbers = ConversationHandler(
        entry_points=[CommandHandler('find_phone_number', findPhoneNumbersCommand)],
        states={
            FIND_PHONE_NUMBER: [MessageHandler(Filters.text & ~Filters.command, findPhoneNumbers)],
            FIND_PHONE_NUMBER_CONFIRMATION: [MessageHandler(Filters.text & ~Filters.command, confirmPhoneNumbers)]
        },
        fallbacks=[]
    )

    convHandlerFindEmails = ConversationHandler(
        entry_points=[CommandHandler('find_email', findEmailCommand)],
        states={
            FIND_EMAIL: [MessageHandler(Filters.text & ~Filters.command, findEmails)],
            FIND_EMAIL_CONFIRMATION: [MessageHandler(Filters.text & ~Filters.command, confirmEmails)]
        },
        fallbacks=[]
    )


    convHandlerVerifyPassword = ConversationHandler(
        entry_points=[CommandHandler('verify_password', verifyPasswordCommand)],
        states={
            VERIFY_PASSWORD: [MessageHandler(Filters.text & ~Filters.command, verifyPassword)],
        },
        fallbacks=[]
    )
     
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", helpCommand))
    dp.add_handler(convHandlerFindPhoneNumbers)
    dp.add_handler(convHandlerFindEmails)
    dp.add_handler(convHandlerVerifyPassword)
    dp.add_handler(CommandHandler("get_release", get_release))
    dp.add_handler(CommandHandler("get_uname", get_uname))
    dp.add_handler(CommandHandler("get_uptime", get_uptime))
    dp.add_handler(CommandHandler("get_df", get_df))
    dp.add_handler(CommandHandler("get_free", get_free))
    dp.add_handler(CommandHandler("get_mpstat", get_mpstat))
    dp.add_handler(CommandHandler("get_w", get_w))
    dp.add_handler(CommandHandler("get_auths", get_auths))
    dp.add_handler(CommandHandler("get_critical", get_critical))
    dp.add_handler(CommandHandler("get_ps", get_ps))
    dp.add_handler(CommandHandler("get_ss", get_ss))
    dp.add_handler(CommandHandler("get_apt_list", get_apt_list))
    dp.add_handler(CommandHandler("search_package", search_package))
    dp.add_handler(CommandHandler("get_services", get_services))
    dp.add_handler(CommandHandler("get_repl_logs", get_repl_logs))
    dp.add_handler(CommandHandler("get_emails", get_emails))
    dp.add_handler(CommandHandler("get_phone_numbers", get_phone_numbers))

    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))

    updater.start_polling()

    updater.idle()

if __name__ == '__main__':
    main()
