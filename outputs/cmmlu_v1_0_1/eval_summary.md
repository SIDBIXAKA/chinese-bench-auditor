# 多模型 Bad Case 实测对比汇总报告

- 样本总数：50 | 已实测条数：50
- 参与模型：model_deepseek_ans=deepseek-ai/DeepSeek-V3, model_qwen_ans=Qwen/Qwen2.5-7B-Instruct

## 一、分歧归因分类统计

| 归因类别 | 样本数 | 含义 |
| :--- | ---: | :--- |
| `MODEL_SPLIT_OR_ERROR` | 14 | 模型之间存在分歧或部分模型推理错误 |
| `SUSPECTED_GOLD_ERROR_MODEL_UNANIMOUS` | 7 | 多模型一致答案且不同于题库金标（高度疑似题库标错） |
| `MODELS_AGREE_WITH_GOLD` | 24 | 多模型作答与原金标一致 |
| `BLIND_CONTEXT_HALLUCINATION` | 4 | 缺失图片/表格上下文，但模型仍强行瞎猜作答（模型幻觉） |
| `BLIND_CONTEXT_ABSTAINED` | 1 | 缺失图片/表格上下文，模型正确识别并拒答 UNANSWERABLE |

## 二、人工复核最终裁决统计（Human Verdicts）

| 人工裁决结论 | 样本数 |
| :--- | ---: |
| `GOLD_CORRECT` | 3 |
| `GOLD_ERROR` | 4 |
| `MODEL_ERROR_GOLD_CORRECT` | 3 |

### 已复核样本明细

- **`dev/elementary_mathematics#1`** -> `GOLD_CORRECT` | 原金标 `D` | verified: 2^4 - 1 = 15 (gold D correct)
- **`test/education#114`** -> `GOLD_ERROR` | 原金标 `A` | verified: should be B (政治经济制度), contradicts test/education#131
- **`test/education#131`** -> `GOLD_CORRECT` | 原金标 `C` | verified: 政治经济制度 (gold C correct)
- **`test/high_school_mathematics#128`** -> `GOLD_ERROR` | 原金标 `C` | verified: 2^4 - 1 = 15, should be A (PR fixed)
- **`test/logical#84`** -> `GOLD_ERROR` | 原金标 `C` | verified: should be D (所有前提真而结论假), contradicts test/logical#85
- **`test/logical#85`** -> `GOLD_CORRECT` | 原金标 `C` | verified: 所有前提真而结论假 (gold C correct)
- **`test/sociology#1`** -> `GOLD_ERROR` | 原金标 `C` | verified: Merton strain theory -> 创新 (A), contradicts test/sociology#74
- **`test/sociology#74`** -> `MODEL_ERROR_GOLD_CORRECT` | 原金标 `A` | verified: gold A (创新) is correct; both DeepSeek & Qwen mispredicted B (反叛)
- **`dev/college_mathematics#1`** -> `MODEL_ERROR_GOLD_CORRECT` | 原金标 `C` | verified: removable discontinuities at x=-1,0,1 (count=3, gold C correct); DeepSeek truncated, Qwen wrong
- **`test/college_mathematics#6`** -> `MODEL_ERROR_GOLD_CORRECT` | 原金标 `D` | verified: removable discontinuities at x=-1,0,1 (count=3, gold D correct); DeepSeek truncated, Qwen wrong

## 三、典型案例明晰（前 15 条已测记录）

- **`dev/elementary_mathematics#1`** (`CHK_CONFLICTING_GOLD_ANSWER`) | 原金标: `D` | model_deepseek_ans=D, model_qwen_ans=B  
  题干：集合A={1，2,3, 4}的真⼦集个数为
- **`test/education#114`** (`CHK_CONFLICTING_GOLD_ANSWER`) | 原金标: `A` | model_deepseek_ans=B, model_qwen_ans=B  
  题干：决定教育性质的根本因素是
- **`test/education#131`** (`CHK_CONFLICTING_GOLD_ANSWER`) | 原金标: `C` | model_deepseek_ans=C, model_qwen_ans=C  
  题干：决定教育性质的根本因素是
- **`test/high_school_mathematics#128`** (`CHK_CONFLICTING_GOLD_ANSWER`) | 原金标: `C` | model_deepseek_ans=A, model_qwen_ans=D  
  题干：集合A={1,2,3,4}的真⼦集个数为
- **`test/logical#84`** (`CHK_CONFLICTING_GOLD_ANSWER`) | 原金标: `C` | model_deepseek_ans=D, model_qwen_ans=D  
  题干：根据演绎有效性原则，论证无效的一个重要标志是
- **`test/logical#85`** (`CHK_CONFLICTING_GOLD_ANSWER`) | 原金标: `C` | model_deepseek_ans=C, model_qwen_ans=C  
  题干：根据演绎有效性原则，论证无效的一个重要标志是
- **`test/sociology#1`** (`CHK_CONFLICTING_GOLD_ANSWER`) | 原金标: `C` | model_deepseek_ans=B, model_qwen_ans=C  
  题干：为了追求社会鼓励的目标，采用了不被社会认可的手段，甚至是违法的手段，这种偏差行为称之为
- **`test/sociology#127`** (`CHK_CONFLICTING_GOLD_ANSWER`) | 原金标: `C` | model_deepseek_ans=C, model_qwen_ans=C  
  题干：价值冲突理论认为，造成社会问题的根本原因是
- **`test/sociology#14`** (`CHK_CONFLICTING_GOLD_ANSWER`) | 原金标: `B` | model_deepseek_ans=A, model_qwen_ans=A  
  题干：假定有些人天生就是不守规矩的人，在这一假定基础上形成的关于偏差行为的解释是
- **`test/sociology#167`** (`CHK_CONFLICTING_GOLD_ANSWER`) | 原金标: `D` | model_deepseek_ans=C, model_qwen_ans=C  
  题干：价值冲突理论认为，造成社会问题的根本原因是
- **`test/sociology#198`** (`CHK_CONFLICTING_GOLD_ANSWER`) | 原金标: `A` | model_deepseek_ans=A, model_qwen_ans=A  
  题干：假定有些人天生就是不守规矩的人，在这一假定基础上形成的关于偏差行为的解释是
- **`test/sociology#74`** (`CHK_CONFLICTING_GOLD_ANSWER`) | 原金标: `A` | model_deepseek_ans=B, model_qwen_ans=B  
  题干：为了追求社会鼓励的目标，采用了不被社会认可的手段，甚至是违法的手段，这种偏差行为称之为
- **`test/genetics#36`** (`CHK_DUPLICATE_OPTIONS`) | 原金标: `B` | model_deepseek_ans=B, model_qwen_ans=C  
  题干：豌豆中，高茎(T)对矮茎(t)为显性，黄子叶(Y)对绿子叶(y)为显性，假定这两个位点的遗传符合孟德尔第二定律，若把真实遗传的高茎黄子叶个体与矮茎绿子叶个体进行杂交，F2代中矮茎黄
- **`dev/ancient_chinese#4`** (`CHK_DEV_TEST_LEAKAGE`) | 原金标: `D` | model_deepseek_ans=D, model_qwen_ans=D  
  题干：按照传统的“六书”体例，“益”字应属
- **`dev/college_law#1`** (`CHK_DEV_TEST_LEAKAGE`) | 原金标: `D` | model_deepseek_ans=D, model_qwen_ans=D  
  题干：以下选项中，属于邻接权客体的是
