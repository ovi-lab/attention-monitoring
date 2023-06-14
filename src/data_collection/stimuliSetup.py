import os
import csv
import random

def generateSequence(name, stimuliPath, sequenceLength):
    """Generate a sequence of images for a gradCPT run.

    The sequence is output to lines of a csv file with two columns:
    'stimulus_path', which gives the absolute path to the stimulus file, and
    'target_type', which specifies whether the stimulus is a 'rare' or a
    'common' target. The sequence consists of randomly selected stimuli such
    that a) each stimulus has 90% probability of being a common target and a
    10% chance of being a rare target, and b) no consecutive stimuli are
    identical.

    Parameters
    ----------
    name : str
        The name of the csv file to write to (including the relative path if
        applicable). Do not include the file extension ('.csv') in `name`.
    stimuliPath : str
        The path to the directory containing the stimuli. Stimuli must be
        organised into two subdirectories `common_target` and `rare_target`,
        which contain the common target stimuli and rare target stimuli
        respectively. Each subdirectory must contain 2 or more stimuli.
    sequenceLength : int
        The length of the generated sequence of stimuli.
    """

    # (For each item in the sequence) probability of stimulus being selected
    # from common targets or rare targets, respectively
    weights = [90, 10]

    commonTargetsPath = os.path.join(stimuliPath, "common_target")
    rareTargetsPath = os.path.join(stimuliPath, "rare_target")

    # Get path to each stimulus and whether it is a common or rare target
    commonTargets = [[os.path.join(commonTargetsPath, f), "common"] for f in
        os.listdir(commonTargetsPath)]
    rareTargets = [[os.path.join(rareTargetsPath, f), "rare"] for f in
        os.listdir(rareTargetsPath)]
    targets = [commonTargets, rareTargets]

    # Write stimuli paths and target types to csv file
    #TODO: ensure probability distribution is correctly implemented
    with open(name + ".csv", 'w') as f:
        writer = csv.writer(f)

        header = ["stimulus_path", "target_type"]
        writer.writerow(header)

        i = [set(range(len(commonTargets))), set(range(len(rareTargets)))]
        lastTargetClass = random.choices([0, 1], weights=weights)[0]
        lastItem = i[lastTargetClass].pop()
        for _ in range(sequenceLength):
            currentTargetClass = random.choices([0, 1], weights=weights)[0]
            currentItem = i[currentTargetClass].pop()
            writer.writerow(targets[currentTargetClass][currentItem])

            i[lastTargetClass].add(lastItem)
            lastTargetClass = currentTargetClass
            lastItem = currentItem





        
    