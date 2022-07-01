import streamlit as st
import pandas as pd
import plotly_express as px
import numpy as np
import gspread
import plotly.graph_objects as go 
st.set_page_config(layout='wide')

# setup credentials
credentials = {
  "type": st.secrets["type"],
  "project_id": st.secrets["project_id"],
  "private_key_id": st.secrets["private_key_id"],
  "private_key": st.secrets["private_key"],
  "client_email": st.secrets["client_email"],
  "client_id": st.secrets["client_id"],
  "auth_uri": st.secrets["auth_uri"],
  "token_uri": st.secrets["token_uri"],
  "auth_provider_x509_cert_url": st.secrets["auth_provider_x509_cert_url"],
  "client_x509_cert_url": st.secrets["client_x509_cert_url"]
}
sheetKey = '1f3gA4sIxLqBYQw7bk1igGGNaFtW7LHtO_7BCCmMS1IQ'
dbSheet1 = 'Survey Data'
dbSheet2 = 'Org Data'

# Load up all our data, caching to limit re-pulls
@st.cache(ttl=1100, allow_output_mutation=True)
def load_dataset():
   gc = gspread.service_account_from_dict(credentials)
   ws1 = gc.open_by_key(sheetKey).worksheet(dbSheet1)
   ws2 = gc.open_by_key(sheetKey).worksheet(dbSheet2)
   sh1 = ws1.get_all_records()
   sh2 = ws2.get_all_records()
   headers1 = sh1.pop(0)
   headers2 = sh2.pop(0)
   df1 = pd.DataFrame(sh1, columns=headers1, copy=True)
   df2 = pd.DataFrame(sh2, columns=headers2, copy=True)
   dlist = (df1, df2)
   return dlist

# get our data loaded into pandas dataframes
dataList = load_dataset()
surveyData = dataList[0]
orgData = dataList[1]

#cleaning tasks
surveyData = surveyData.astype(str)
surveyData.columns = ['SID', 'System', 'School', 'Type', 'Method', 'Date', 'Primary', 'Secondary', 'Tertiary', 'Quaternary', 'Submitter', 
                    'ChangeClarity', 'RoleClarity', 'GoalConfident', 'Equipped', 'Supported', 'Understanding', 'Valuable', 'WorkClarity', 'Learned', 'Recommend']

#pesky bad data
surveyData.at[surveyData.index[surveyData['Date'] == 'Leader Coaching'].tolist()[0],'Type']='Leader Coaching'
surveyData.at[surveyData.index[surveyData['Date'] == 'Leader Coaching'].tolist()[0],'Date']='7/15/2021'

#something for blanks
surveyData.replace('', np.nan, inplace=True)

#remap responses to ints and tidy types
resp_dict = {'Strongly Agree':7, 'Agree':6, 'Somewhat Agree':5, 'Neutral':4, 'Somewhat Disagree':3, 'Disagree':2, 'Strongly Disagree':1}
sData = surveyData.replace({'ChangeClarity':resp_dict,'RoleClarity':resp_dict,'GoalConfident':resp_dict,'Equipped':resp_dict,'Supported':resp_dict,
                    'Understanding':resp_dict,'Valuable':resp_dict,'WorkClarity':resp_dict,'Learned':resp_dict,'Recommend':resp_dict})
type_dict = {'ChangeClarity':'Int64', 'RoleClarity':'Int64', 'GoalConfident':'Int64', 'Equipped':'Int64', 'Supported':'Int64', 'Understanding':'Int64', 
            'Valuable':'Int64', 'WorkClarity':'Int64', 'Learned':'Int64', 'Recommend':'Int64'}
sData = sData.astype(type_dict)
sData['Date'] = pd.to_datetime(sData['Date'])
sData['NumStaff'] = 4-sData[['Primary', 'Secondary', 'Tertiary', 'Quaternary']].isnull().sum(axis=1)

#some charting dictionaries
sample_dict = {'Monthly':'M', 'Quarterly':'Q', 'Weekly':'W'}
dim_dict = {'Clarity in Change Needed':'ChangeClarity', 'Clarity in Roles and Responsibilities':'RoleClarity', 'Confident in the Goals':'GoalConfident', 'More Equipped':'Equipped', 'Equipped and Supported':'Supported', 
            'Understand Instruction State':'Understanding','Valuable Use of Time':'Valuable', 'Clear in Work Ahead': 'WorkClarity', 'Learned Something':'Learned', 'Would Recommend':'Recommend',
            'Clarity of Communication':['ChangeClarity', 'RoleClarity', 'Understanding', 'WorkClarity'], 'Equipping People for Success':['Equipped', 'Supported'], 'Evaluative Metrics':['Recommend', 'GoalConfident', 'Learned', 'Valuable']}

choice_dict = {'No, direct options':['Clarity in Change Needed','Clarity in Roles and Responsibilities', 'Confident in the Goals', 'More Equipped', 'Equipped and Supported', 
                                'Understand Instruction State','Valuable Use of Time', 'Clear in Work Ahead', 'Learned Something', 'Would Recommend'], 'Yes, aggregate':['Clarity of Communication', 'Equipping People for Success', 'Evaluative Metrics']}

category_dict = {'Clarity of Communication':['ChangeClarity', 'RoleClarity', 'Understanding', 'WorkClarity'], 'Equipping People for Success':['Equipped', 'Supported'], 'Evaluative Metrics':['Recommend', 'GoalConfident', 'Learned', 'Valuable']}

#Options Selecting
surveySelect = st.sidebar.multiselect('Survey Type', surveyData['Type'].unique())
with st.sidebar:st.caption('Filter by different survey types. Default: all')
with st.sidebar:st.markdown("""---""")
with st.sidebar:st.caption('Select options for viewing, either inspecting each survey category, or aggregating them across thematic collections.')
chartGrouping = st.sidebar.selectbox('Aggregate?', choice_dict.keys())
chartMetric = st.sidebar.radio('Choose Option', choice_dict[chartGrouping])
with st.sidebar:st.markdown("""---""")
chartSample = st.sidebar.radio('Sampling Rate', ['Weekly','Monthly','Quarterly'])


#Process options now via the dictionaries, add in the date to allow for resampling across the time period
#that is desired, and provide the mean across the category for that requested periods.

#first, do we have survey types selcted?
filtData = sData[sData['Type'].isin(surveySelect)]

if(len(surveySelect)>0):
    choiceData = pd.DataFrame(filtData[dim_dict[chartMetric]])
else:
    choiceData = pd.DataFrame(sData[dim_dict[chartMetric]])
choiceData['Date'] = sData['Date']
choiceData =choiceData.set_index('Date').resample(sample_dict[chartSample]).mean()
choiceData['Mean'] = choiceData.mean(axis=1)
choiceFilt = choiceData[choiceData['Mean']>0]

#let's get the graph, build it and show it
st.write('How do partners feel about the work? Explore either by individual questions, or across similar categories, breaking down main themes, such as the clarity in team communication, ' 
        'how well the team is preparing partners for success, or through simple evaluative metrics such as whether they found the work valuable or would recommend it to others. Explore change over time and where things are headed. '
         'For aggregated categories, explore correlation between the different survey questions.')
col1, col2 = st.columns(2)
with col1:
    if(choiceFilt.shape[0]>0):
        
        figg = px.scatter(choiceFilt, x=choiceFilt.index, y=choiceFilt['Mean'], trendline='ols', trendline_color_override='red')
        figg.update_traces(mode = 'lines')
        st.plotly_chart(figg)
    else: st.write('Select more survey types or a different survey question.')

corr = choiceFilt.corr()
corr = corr.loc[corr.index.values != 'Mean',corr.columns != 'Mean']

with col2:
    fig = go.Figure()
    fig.add_trace(go.Heatmap(x=corr.columns,y=corr.index, z=np.array(corr)))
    if(chartGrouping != 'No, direct options'):
        st.plotly_chart(fig)
st.markdown("""---""")

st.write('How are staff being utilized? Is there a relationship between how many staff are used, and the liklihood that participants will recommend this to others?')

scol1, scol2 = st.columns(2)

numRec = sData[['NumStaff', 'Recommend']]

with scol1:
    nsfig = px.histogram(numRec, x='NumStaff', title='Count per number of staff facilitating', labels={'NumStaff':'Number of Facilitators'})
    st.plotly_chart(nsfig)

with scol2:
    nstaffmean = numRec.groupby('NumStaff').mean()
    st.plotly_chart(px.bar(nstaffmean, x=nstaffmean.index, y='Recommend', title='Likelihood to Recommend (mean) vs. Number of Facilitators', labels={'NumStaff':'Number of Facilitators', 'Recommend':'Liklihood to Recommend (mean)'}))

st.markdown("""---""")