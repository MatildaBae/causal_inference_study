# -*- coding: utf-8 -*-
"""CausalInference_voting.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1NMiA5vpv6It8aRDze9T7pWaularrysRC
"""

# 먼저 라이브러리 설치 (설치되지 않은 경우)
!pip install pyreadstat

# pyreadstat으로 Stata 파일 읽기
import pyreadstat

df, meta = pyreadstat.read_dta('ct_felon2.dta')

# 데이터 확인
print(df.head())

"""### 1. 로지스틱 회귀 계수 추정 및 95% 신뢰 구간"""

print(df.dtypes)

import pandas as pd
import statsmodels.api as sm
import numpy as np

# 데이터 준비
df_encoded = pd.get_dummies(df, columns=['crime'], drop_first=True)

# bool 타입의 열들을 float64 타입으로 변환
df_encoded = df_encoded.astype({col: 'float64' for col in df_encoded.columns if df_encoded[col].dtype == 'bool'})

# X는 공변량 (v08, age, days_served, timesincerelease 등), mail 변수를 제외
X = df_encoded[['v08', 'age', 'days_served', 'timesincerelease'] + [col for col in df_encoded.columns if 'crime_' in col]]

# A는 처치 변수 (mail)
A = df_encoded['mail']

# Y는 결과 변수 (reg)
Y = df_encoded['reg']

# X에 처치 변수 A(mail) 추가 (X와 A 모두 포함)
X_with_A = sm.add_constant(X.join(A))  # 상수를 추가하여 회귀 모델을 적합시킬 준비

# 로지스틱 회귀 모델 적합
logit_model = sm.Logit(Y, X_with_A)
result = logit_model.fit()

# 결과 출력
print(result.summary())

# mail 변수의 계수는 0.2872로 추정. 이는 log-odds.
# 우편을 받았을 때, 투표 등록의 log-odds raised by 0.2872

# 조건부 승산비 (mail 변수의 계수 추출 후 exp 적용)
odds_ratio = np.exp(result.params['mail'])
conf = result.conf_int()
conf_odds_ratio = np.exp(conf.loc['mail'])
print(f"Odds Ratio for mail: {odds_ratio}")
print(f"95% CI for Odds Ratio: [{conf_odds_ratio[0]}, {conf_odds_ratio[1]}]")

# 우편물을 받은 사람들이 우편물을 받지 않은 사람들보다 투표 등록을 할 오즈가 약 33% 더 높다는 것
# 오즈비의 95% 신뢰 구간은 [1.0909, 1,6277]

"""### 2-1. Difference-in-means 추정 및 95% 신뢰 구간"""

import numpy as np
import scipy.stats as stats

# Difference-in-means 계산
mean_mail = df_encoded[df_encoded['mail'] == 1]['reg'].mean()  # 우편물을 받은 그룹
mean_no_mail = df_encoded[df_encoded['mail'] == 0]['reg'].mean()  # 우편물을 받지 않은 그룹

# Difference-in-means 추정량
diff_in_means = mean_mail - mean_no_mail

# 표준 오차 계산
n_mail = df_encoded[df_encoded['mail'] == 1]['reg'].count()  # 우편물을 받은 그룹의 샘플 수
n_no_mail = df_encoded[df_encoded['mail'] == 0]['reg'].count()  # 우편물을 받지 않은 그룹의 샘플 수
std_mail = df_encoded[df_encoded['mail'] == 1]['reg'].std()  # 우편물을 받은 그룹의 표준 편차
std_no_mail = df_encoded[df_encoded['mail'] == 0]['reg'].std()  # 우편물을 받지 않은 그룹의 표준 편차

# 두 그룹의 표준 오차
std_err_diff = np.sqrt((std_mail**2 / n_mail) + (std_no_mail**2 / n_no_mail))

# 95% 신뢰 구간 계산
ci_low, ci_high = stats.norm.interval(0.95, loc=diff_in_means, scale=std_err_diff)

print(f"Difference-in-means Estimate: {diff_in_means}")
print(f"95% Confidence Interval: [{ci_low}, {ci_high}]")

"""### 2-2. Horvitz-Thompson 추정 및 95% 신뢰 구간"""

# 성향 점수 계산 (로지스틱 회귀)
propensity_model = sm.Logit(df_encoded['mail'], X).fit()
df_encoded['propensity_score'] = propensity_model.predict(X)

# 가중치 계산
df_encoded['weight'] = df_encoded['mail'] / df_encoded['propensity_score'] + (1 - df_encoded['mail']) / (1 - df_encoded['propensity_score'])

# Horvitz-Thompson 추정량
ht_estimator = (df_encoded['weight'] * df_encoded['reg']).mean()

# Horvitz-Thompson 표준 오차 및 95% 신뢰 구간 계산
ht_var = (df_encoded['weight'] * (df_encoded['reg'] - ht_estimator)**2).mean()
ht_std_err = np.sqrt(ht_var / df_encoded.shape[0])

ci_low, ci_high = stats.norm.interval(0.95, loc=ht_estimator, scale=ht_std_err)

print(f"Horvitz-Thompson Estimate: {ht_estimator}")
print(f"95% Confidence Interval: [{ci_low}, {ci_high}]")

"""### 3. Parametric Plug-in 방식(using OLS) 및 95% 신뢰 구간"""

# OLS 모델 적합
ols_model = sm.OLS(df_encoded['reg'], X.join(A))
ols_result = ols_model.fit()

# Parametric Plug-in 추정량 (mail 변수의 계수 사용)
ols_mail_coef = ols_result.params['mail']

# 95% 신뢰 구간 계산
conf_ols = ols_result.conf_int().loc['mail']

print(f"Parametric Plug-in Estimate (OLS): {ols_mail_coef}")
print(f"95% Confidence Interval (OLS): [{conf_ols[0]}, {conf_ols[1]}]")

"""### 4. Doubly Robust"""

# 데이터 준비
df_encoded = pd.get_dummies(df, columns=['crime'], drop_first=True)

# bool 타입의 열들을 float64 타입으로 변환
df_encoded = df_encoded.astype({col: 'float64' for col in df_encoded.columns if df_encoded[col].dtype == 'bool'})

df_encoded.head()

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
import statsmodels.api as sm
from statsmodels.stats.weightstats import DescrStatsW

df = df_encoded

# 1. Propensity score model (mail assignment)
X_ps = df[['v08', 'age', 'days_served', 'timesincerelease'] + list(df.columns[df.columns.str.startswith('crime_')])]  # Include crime dummies
mail = df['mail']

# Logistic regression for propensity score estimation
propensity_model = LogisticRegression()
propensity_model.fit(X_ps, mail)

# Predict propensity scores
propensity_scores = propensity_model.predict_proba(X_ps)[:, 1]

# 2. Outcome model (reg)
X_outcome = sm.add_constant(df[['mail', 'v08', 'age', 'days_served', 'timesincerelease'] + list(df.columns[df.columns.str.startswith('crime_')])])  # Include crime dummies
outcome_model = sm.Logit(df['reg'], X_outcome)
outcome_result = outcome_model.fit()

# Predicted outcomes for both treated (mail=1) and untreated (mail=0)
df['y_hat_1'] = outcome_result.predict(X_outcome.assign(mail=1))  # mail=1 scenario
df['y_hat_0'] = outcome_result.predict(X_outcome.assign(mail=0))  # mail=0 scenario

# 3. Compute doubly robust estimator
df['dr_estimate'] = (df['mail'] / propensity_scores) * (df['reg'] - df['y_hat_1']) + df['y_hat_1'] - \
                    ((1 - df['mail']) / (1 - propensity_scores)) * (df['reg'] - df['y_hat_0']) + df['y_hat_0']

# 4. Calculate the Average Treatment Effect (ATE)
ate = np.mean(df['dr_estimate'])

# 5. Confidence Interval using weighted standard error
ate_se = DescrStatsW(df['dr_estimate']).std_mean
ci_lower = ate - 1.96 * ate_se
ci_upper = ate + 1.96 * ate_se

print(f"Estimated ATE: {ate}")
print(f"95% Confidence Interval: [{ci_lower}, {ci_upper}]")

"""### 4-1. Semiparametric/Bias-corrected 추정(로지스틱 회귀 모델 적합 후, 보정)"""

import pandas as pd
import statsmodels.api as sm
import numpy as np
from sklearn.neighbors import KernelDensity
from scipy import stats

# 데이터 준비
df_encoded = pd.get_dummies(df, columns=['crime'], drop_first=True)

# bool 타입의 열들을 float64 타입으로 변환
df_encoded = df_encoded.astype({col: 'float64' for col in df_encoded.columns if df_encoded[col].dtype == 'bool'})

# X는 공변량 (v08, age, days_served, timesincerelease 등), mail 변수를 제외
X = df_encoded[['v08', 'age', 'days_served', 'timesincerelease'] + [col for col in df_encoded.columns if 'crime_' in col]]

# A는 처치 변수 (mail)
A = df_encoded['mail']

# Y는 결과 변수 (reg)
Y = df_encoded['reg']

# X에 처치 변수 A(mail) 추가
X_with_A = sm.add_constant(X.join(A))

# Step 1: 로지스틱 회귀 모델 적합
logit_model = sm.Logit(Y, X_with_A)
logit_result = logit_model.fit()

# Doubly Robust 방법으로 다시 생각
# Step 2: 비모수적 방법 (커널 밀도 추정)으로 편향 보정
# 커널 밀도 추정기를 사용하여 편향 보정
kde = KernelDensity(kernel='gaussian', bandwidth=0.5).fit(X_with_A)
log_density = kde.score_samples(X_with_A)

# 편향 보정 적용 (로그 오즈에 대해 보정)
bias_corrected_estimator = logit_result.predict() - log_density.mean()

# Step 3: 95% 신뢰 구간 계산
ci_low, ci_high = stats.norm.interval(0.95, loc=bias_corrected_estimator.mean(), scale=np.std(bias_corrected_estimator))

print(f"Bias-corrected Estimate: {bias_corrected_estimator.mean()}")
print(f"95% Confidence Interval: [{ci_low}, {ci_high}]")

"""### 4-2. Semiparametric/Bias-corrected 추정(OLS 모델 적합 후, 보정)"""

# Step 1: OLS 모델 적합
ols_model = sm.OLS(Y, X_with_A)
ols_result = ols_model.fit()

# OLS 기반 추정 및 커널 밀도 추정 적용
bias_corrected_estimator_ols = ols_result.predict() - log_density.mean()

# 95% 신뢰 구간 계산
ci_low_ols, ci_high_ols = stats.norm.interval(0.95, loc=bias_corrected_estimator_ols.mean(), scale=np.std(bias_corrected_estimator_ols))

print(f"Bias-corrected Estimate (OLS): {bias_corrected_estimator_ols.mean()}")
print(f"95% Confidence Interval (OLS): [{ci_low_ols}, {ci_high_ols}]")

