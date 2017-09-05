import random as rand
score_lines = ["hgvs,score,epsilon,se\n"]
count_lines = ["hgvs,count\n"]

for i in range(0, 1000):
    if i == 0:
        hgvs = "_wt"
    else:
        hgvs = "c.{}A>T".format(i)

    score = rand.random()
    epsilon = rand.random()
    se = rand.random()
    count = rand.randint(0, 100)

    line = "{},{},{},{}\n".format(hgvs, score, epsilon, se)
    score_lines.append(line)

    line = "{},{}\n".format(hgvs, count)
    count_lines.append(line)

with open("scores.txt", 'wt') as fp:
    for line in score_lines:
        fp.writelines(line)

with open("counts.txt", 'wt') as fp:
    for line in count_lines:
        fp.writelines(line)
