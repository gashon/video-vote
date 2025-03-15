# Video Vote Repository
## Instructions for Organizing Videos and Configuration
1. Place the Videos
Create the following directory structure in the repository:
```
video/
  ├── 9sec/
  │   ├── [model_name1]/
  │   │   ├── 000.mp4
  │   │   ├── 001.mp4
  │   │   ├── 002.mp4
  │   │   └── ... 
  │   │   └── 100.mp4
  │   ├── [model_name2]/
  │   ├── [model_name3]/
  │   └── [model_name4]/
  └── prompts/
      ├── 001.txt
      └── 100.txt
```

2. Update Model Name List
Change the model name list in the following file `streamlit_pages.py - Line 12`

3. Update Text File Directory
Modify the text file directory you selected in the first step: `streamlit_pages.py - Line 142`

4. Update Videos Directory
Change the videos directory you selected in the first step: `streamlit_pages.py - Line 142`

### How to run it on your own machine

1. Install the requirements

   ```
   $ pip install -r requirements.txt
   ```

2. Run the app

   ```
   $ streamlit run streamlit_app.py
   ```
