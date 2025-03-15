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
Modify the text file directory you selected in the first step: `streamlit_pages.py - Line 162`

4. Update Videos Directory
Change the videos directory you selected in the first step: `streamlit_pages.py - Line 142`

5. (Optional) Evaluation Settings
The default setting is to evaluate 500 videos, using 5 criteria, 5 times each with 250 evaluators (each evaluator will make 50 evaluations). If you want to run a test before the actual release with 100 videos, you will need to modify certain numbers in batch_manager.py between lines 3 and 10.

For example, if you want to evaluate 100 videos with 5 criteria, 1 time each, and 5 evaluators, you would set:
```python
NUM_PROMPTS = 100
NUM_CRITERIA = 5
TOTAL_EVALUATIONS = NUM_PROMPTS * NUM_CRITERIA

NUM_EVALUATORS = 5
NUM_BATCHES = NUM_EVALUATORS // 1  # 5
NUM_GROUPS = NUM_BATCHES // NUM_CRITERIA  # 1
NUM_PROMPTS_PER_GROUP = NUM_PROMPTS // NUM_GROUPS  # 100
```

### How to run it on your own machine

1. Install the requirements

   ```
   $ pip install -r requirements.txt
   ```

2. Run the app

   ```
   $ streamlit run streamlit_app.py
   ```
