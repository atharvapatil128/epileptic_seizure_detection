import streamlit as st
from firebase_admin import auth, credentials, initialize_app, App, get_app
from uuid import uuid4
import requests
import pandas as pd
import plotly.express as px
from twilio.rest import Client
import phonenumbers
import pickle
import xgboost

# First thing in your script, set the page config.
if 'page_config_set' not in st.session_state:
    st.set_page_config(
        page_title='Epileptic Seizure Detection Dashboard', layout='wide')
    st.session_state['page_config_set'] = True

# Function to safely get the existing app or initialize a new one


def get_firebase_app():
    # Try getting the existing app
    try:
        return get_app()
    # No app initialized yet, create a new one
    except ValueError as e:
        cred = credentials.Certificate(
            "capstone-f-firebase-adminsdk-qrx4h-9f74c2e542.json")
        return initialize_app(cred)


# Initialize Firebase app
firebase_app = get_firebase_app()


def create_user(email, password, role):
    user = auth.create_user(email=email, password=password, app=firebase_app)
    auth.set_custom_user_claims(user.uid, {'role': role}, app=firebase_app)
    return user.uid


def verify_password(email, password):
    # Replace with your Firebase API key
    API_KEY = "AIzaSyDZLbqxadTCXtkv1tTjkSFWU9gv4Li-ArU"

    details = {
        'email': email,
        'password': password,
        'returnSecureToken': True,
    }

    try:
        # Make a request to the Firebase REST API for authentication
        response = requests.post(
            f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={API_KEY}",
            data=details
        )
        response.raise_for_status()
        # If the request is successful, we get a response containing the ID token
        id_token = response.json().get("idToken")
        user_data = auth.get_user_by_email(email, app=firebase_app)
        # Store custom claims and other necessary session data
        st.session_state['authenticated'] = True
        st.session_state['user_role'] = user_data.custom_claims.get(
            'role', 'patient')  # default to 'patient'
        st.session_state['user_token'] = id_token
        return id_token
    except requests.exceptions.RequestException as error:
        # Handle error responses from the REST API here
        print(error)
        st.session_state['authenticated'] = False
        return None


def reset_password(email):
    return auth.generate_password_reset_link(email, app=firebase_app)


def change_password(user_id, new_password):
    auth.update_user(user_id, password=new_password, app=firebase_app)
    return True


# Define your Streamlit authentication interface here
def auth_interface():
    with st.container():
        unique_session_id = str(uuid4())[:8]
        st.title('Epileptic Seizure Detection System 🧠')
        st.header('🔑 User Authentication')
        st.write(
            "Welcome to the Epileptic Seizure Detection System! Please login or register to continue.")

        tab1, tab2, tab3, tab4 = st.tabs(
            ["Login", "Sign Up", "Forgot Password", "Change Password"])

        with tab1:
            st.subheader("Login")
            email_login = st.text_input("Email", key="login_email_tab")
            password_login = st.text_input(
                "Password", type="password", key="login_password")
            if st.button("Sign In"):
                user_authenticated = verify_password(
                    email_login, password_login)
                if user_authenticated:
                    st.session_state['authenticated'] = True
                    st.balloons()  # optional: to show balloons on successful login
                    st.success("Welcome to the Dashboard!")
                    st.rerun()  # Use st.rerun() instead of st.experimental_rerun()
                else:
                    st.error("Invalid username/password")

        with tab2:
            st.subheader("Sign Up")
            email_signup = st.text_input("Email", key="signup_email_tab")
            password_signup = st.text_input(
                "Password", type="password", key="signup_password")
            role_signup = st.radio(
                "Role", ["Doctor", "Patient"], key="signup_role")
            if st.button("Create Account"):
                user_id = create_user(
                    email_signup, password_signup, role_signup.lower())
                st.success(f"Account created for: {email_signup}")

        with tab3:
            st.subheader("Forgot Password")
            email_reset = st.text_input("Email", key="reset_email_tab")
            if st.button("Reset Password"):
                reset_link = reset_password(email_reset)
                st.info(f"Password reset link sent to: {email_reset}")

        with tab4:
            st.subheader("Change Password")
            user_id_change = st.text_input("User ID", key="change_user_id_tab")
            new_password = st.text_input(
                "New Password", type="password", key="new_password_tab")
            if st.button("Change Password"):
                change_password(user_id_change, new_password)
                st.success("Password changed successfully")


# Check the session state to determine whether to show auth interface or dashboard
# if 'authenticated' not in st.session_state:
#   st.session_state['authenticated'] = False

# if not st.session_state['authenticated']:
#    auth_interface()
# else:
#    st.success("Welcome to the Dashboard!")


# Define your model load and prediction functions here
def load_model():
    with open('./model/model.pkl', 'rb') as file:
        model = pickle.load(file)
    return model


model = load_model()


def prepare_data(data_file):
    df = pd.read_csv(data_file)
    return df


def predict(model, data):
    # Assuming model.predict_proba() returns probabilities for class 1
    probabilities = model.predict_proba(data)[:, 1]
    # Check if any probability exceeds the threshold
    seizure_detected = any(prob > 0.5 for prob in probabilities)
    return seizure_detected, max(probabilities)


# Define your main app logic


def validate_phone_number(number):
    try:
        parsed_number = phonenumbers.parse(number)
        return phonenumbers.is_valid_number(parsed_number)
    except phonenumbers.NumberParseException:
        return False


def send_sms_alert(message, phone_numbers):
    account_sid = 'AC2a7fd32ada3c18ec93600f7fc79eee94'
    auth_token = 'e8601ec9938e810853d7a938ffe1aabc'
    client = Client(account_sid, auth_token)

    valid_numbers = [
        num for num in phone_numbers if validate_phone_number(num)]
    for number in valid_numbers:
        client.messages.create(
            body=message,
            from_='+12563848578',
            to=number
        )


def display_patient_dashboard():
    # st.sidebar.title("Navigation")
    st.title('🧠 Epileptic Seizure Detection Dashboard')

    with st.sidebar:
        st.header('Patient Information 📝')
        patient_id = st.text_input('Patient Name')
        patient_age = st.number_input('Age', step=1)
        patient_gender = st.selectbox(
            'Gender', ['Male', 'Female', 'Other'])
        patient_number = st.text_input('Phone Number (e.g., +911234567890)')
        patient_address = st.text_input('Address')

        # Save button
        if st.button('Save Patient Info'):
            # Using session state to temporarily show a success message
            st.session_state.info_saved = True

        if 'info_saved' in st.session_state and st.session_state.info_saved:
            st.success("Patient information saved!")
            # Set a timer to clear the message after a few seconds
            import time
            time.sleep(3)  # Pause for 3 seconds with the success message
            st.session_state.info_saved = False  # Reset the flag

        st.header('SMS Alert Settings ⚙️')
        notification_threshold = st.slider(
            'Notification Threshold', 0.0, 1.0, 0.5, key='notif_threshold')
        healthcare_provider_number = st.text_input(
            "Primary Healthcare Provider Number (e.g., +911234567890)")
        local_hospital_number = st.text_input(
            "Local Emergency Number (e.g., +912345678910)")

    if st.sidebar.button('Logout', key='logout_button'):
        # Reset the session state on logout
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

        # Check if patient information is filled
    patient_info_complete = all(
        [patient_id, patient_age, patient_gender, patient_address, patient_number])

    # Main Content Area - Using Containers in Columns
    col1, col2 = st.columns(2)  # Split into two columns

    with col1:
        with st.container():
            st.subheader('Real-time EEG Monitoring 📈')
            data_file = st.file_uploader("Upload EEG Data", type=[
                'csv', 'xlsx'], help='Upload EEG data file here for analysis.')
            if data_file is not None:
                df = pd.read_csv(data_file)
                fig = px.line(df.iloc[:500], y=df.columns[:5], labels={
                    'value': 'Amplitude', 'index': 'Index'}, template="plotly_dark")
                fig.update_layout(plot_bgcolor='rgba(0,0,0,0)',
                                  paper_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig, use_container_width=True)

    with col2:
        with st.container():
            st.subheader('Seizure Detection Feedback 🔍')
            if data_file is not None and patient_info_complete:
                run_detection = st.button('Run Detection')
                if run_detection:
                    # Get the results and probabilities from the model
                    seizure_detected, max_probability = predict(model, df)
                    # Display results based on the model's prediction
                    if seizure_detected:
                        st.error("Seizure Alert! Immediate attention required.")
                        st.write(
                            f"Maximum seizure probability detected: {max_probability:.2f}")
                        if max_probability >= st.session_state['notif_threshold']:
                            message = f"Urgent: Seizure detected for {patient_id} (Age: {patient_age}, Gender: {patient_gender}, Phone: {patient_number}, Address: {patient_address}). Immediate attention required."
                            # Check if phone numbers are valid before sending SMS
                            if validate_phone_number(healthcare_provider_number) and validate_phone_number(local_hospital_number):
                                send_sms_alert(
                                    message, [healthcare_provider_number, local_hospital_number])
                                st.success('🚨 Alert Sent via SMS')
                            else:
                                st.error(
                                    "Invalid phone number(s). Please check the format.")
                    else:
                        st.success("No seizure detected.")
                        st.write(
                            f"Maximum seizure probability detected: {max_probability:.2f}")
                else:
                    st.info('No alert sent. Confidence below threshold.')
            else:
                st.warning(
                    "Please complete patient information to enable detection.")

        # Historical Data and Alerts Section
    with st.expander("Historical EEG Recordings 🗂️", expanded=False):
        st.write("Historical data overview goes here.")

    st.header('Notifications and Alerts 🛎️')
    if st.button('Send Test Alert'):
        message = "Test alert from Epileptic Seizure Detection System."
        if validate_phone_number(healthcare_provider_number) and validate_phone_number(local_hospital_number):
            send_sms_alert(
                message, [healthcare_provider_number, local_hospital_number])
            st.success('📤 Test Alert Sent via SMS')
        else:
            st.error("Invalid phone number(s). Please check the format.")
        st.success('📤 Test Alert Sent via SMS')


def display_doctor_dashboard():
    # st.sidebar.title("Navigation")
    st.title('🧠 Epileptic Seizure Detection Dashboard')

    with st.sidebar:
        st.header('Patient Information 📝')
        patient_id = st.text_input('Patient ID')
        patient_age = st.number_input('Age', step=1)
        patient_gender = st.selectbox(
            'Gender', ['Male', 'Female', 'Other'])

        # Save button
        if st.button('Save Patient Info'):
            # Using session state to temporarily show a success message
            st.session_state.info_saved = True

        if 'info_saved' in st.session_state and st.session_state.info_saved:
            st.success("Patient information saved!")
            # Set a timer to clear the message after a few seconds
            import time
            time.sleep(3)  # Pause for 3 seconds with the success message
            st.session_state.info_saved = False  # Reset the flag

    if st.sidebar.button('Logout', key='logout_button'):
        # Reset the session state on logout
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

        # Check if patient information is filled
    patient_info_complete = all([patient_id, patient_age, patient_gender])

    # Main Content Area - Using Containers in Columns
    col1, col2 = st.columns(2)  # Split into two columns

    with col1:
        with st.container():
            st.subheader('Real-time EEG Monitoring 📈')
            data_file = st.file_uploader("Upload EEG Data", type=[
                'csv', 'xlsx'], help='Upload EEG data file here for analysis.')
            if data_file is not None:
                df = pd.read_csv(data_file)
                fig = px.line(df.iloc[:500], y=df.columns[:5], labels={
                    'value': 'Amplitude', 'index': 'Index'}, template="plotly_dark")
                fig.update_layout(plot_bgcolor='rgba(0,0,0,0)',
                                  paper_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig, use_container_width=True)

    with col2:
        with st.container():
            st.subheader('Seizure Detection Feedback 🔍')
            if data_file is not None and patient_info_complete:
                run_detection = st.button('Run Detection')
                if run_detection:
                    # Get the results and probabilities from the model
                    seizure_detected, max_probability = predict(model, df)
                    if seizure_detected:
                        st.error("Seizure Alert! Immediate attention required.")
                        st.write(
                            f"Maximum seizure probability detected: {max_probability:.2f}")
                    else:
                        st.success("No seizure detected.")
                        st.write(
                            f"Maximum seizure probability detected: {max_probability:.2f}")
            else:
                st.warning(
                    "Please complete patient information to enable detection.")

        # Historical Data and Alerts Section
    with st.expander("Historical EEG Recordings 🗂️", expanded=False):
        st.write("Historical data overview goes here.")


def dashboard():
    if 'user_role' not in st.session_state:
        st.error("User role not set. Please log in again.")
        return

    if st.session_state['user_role'] == 'doctor':
        st.sidebar.title("Doctor's Dashboard")
        # Doctor-specific UI elements
        display_doctor_dashboard()
    else:
        st.sidebar.title("Patient's Dashboard")
        # Patient-specific UI elements
        display_patient_dashboard()


def main():
    if 'page_config_set' not in st.session_state:
        st.session_state['page_config_set'] = True

    if 'authenticated' not in st.session_state:
        st.session_state['authenticated'] = False

    if not st.session_state['authenticated']:
        auth_interface()
    else:
        dashboard()


if __name__ == '__main__':
    main()
