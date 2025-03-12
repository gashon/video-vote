import numpy as np

NUM_PROMPTS = 500
NUM_CRITERIA = 5
TOTAL_EVALUATIONS = NUM_PROMPTS*NUM_CRITERIA

NUM_EVALUATORS = 250
NUM_BATCHES = NUM_EVALUATORS//5 # 50
NUM_GROUPS = NUM_BATCHES//NUM_CRITERIA # 10
NUM_PROMPTS_PER_GROUP = NUM_PROMPTS//NUM_GROUPS # 50

def create_batches(return_reverse=False):
    batches = {k:[] for k in range(NUM_BATCHES)}
    batches_reverse = np.ones((NUM_CRITERIA, NUM_PROMPTS), dtype=int)*(-1)
    for group in range(NUM_GROUPS):
        for criteria_idx in range(NUM_CRITERIA):
            batch_idx = criteria_idx + group*NUM_CRITERIA
            for prompt_idx in range(group*NUM_PROMPTS_PER_GROUP, (group+1)*NUM_PROMPTS_PER_GROUP):
                batch_idx = batch_idx%NUM_CRITERIA + group*NUM_CRITERIA
                batches[batch_idx].append((prompt_idx, criteria_idx))
                batches_reverse[criteria_idx][prompt_idx] = batch_idx
                batch_idx += 1
        
    # sanity check and sort
    assert np.sum(batches_reverse==-1)==0
    for batch_idx in range(NUM_BATCHES):
        batches[batch_idx] = sorted(batches[batch_idx])
        assert np.sum(batches_reverse == batch_idx) == 50
        assert len(batches[batch_idx]) == 50
    
    if return_reverse:
        return batches, batches_reverse
    
    return batches

if __name__=="__main__":
    batches, batches_reverse = create_batches(return_reverse=True)

    print('First group of evaluators (row - criteria, column - prompt, entries - batch id):')
    print(batches_reverse[:, :NUM_PROMPTS_PER_GROUP])
    print(batches_reverse[:, NUM_PROMPTS_PER_GROUP:2*NUM_PROMPTS_PER_GROUP])