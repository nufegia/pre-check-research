responses <- read.csv("raw_responses.csv")
clean <- na.omit(responses)
print(t.test(stress_score ~ group, data = clean))
