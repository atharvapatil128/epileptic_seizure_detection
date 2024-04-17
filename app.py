import streamlit as st
import pandas as pd
import plotly.express as px

# Function to load model and predict - placeholder


def load_model():
    pass


def predict(model, data):
    return "No Seizure", 0.5  # placeholder


model = load_model()

# Setup page config
st.set_page_config(
    page_title='Epileptic Seizure Detection Dashboard', layout='wide')

st.title('🧠 Epileptic Seizure Detection Dashboard')

# Sidebar: Patient Information and Settings
with st.sidebar:
    st.header('Patient Information 📝')
    patient_id = st.text_input('Patient ID')
    patient_age = st.number_input('Age', step=1)
    patient_gender = st.selectbox('Gender', ['Male', 'Female', 'Other'])

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

    st.header('Settings ⚙️')
    notification_threshold = st.slider('Notification Threshold', 0.0, 1.0, 0.5)
    alert_method = st.selectbox('Alert Method', ['SMS', 'Email'])


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
                result, confidence = predict(model, df)
                st.metric(label="Classification Result", value=result)
                st.metric(label="Confidence Score", value=f"{confidence:.2f}")
                if result == 'Seizure Detected' and confidence > notification_threshold:
                    st.success('🚨 Alert Sent via ' + alert_method)
        else:
            st.warning(
                "Please complete patient information to enable detection.")

# Historical Data and Alerts Section
with st.expander("Historical EEG Recordings 🗂️", expanded=False):
    st.write("Historical data overview goes here.")

st.header('Notifications and Alerts 🛎️')
if st.button('Send Test Alert'):
    st.success('📤 Test Alert Sent via ' + alert_method)
