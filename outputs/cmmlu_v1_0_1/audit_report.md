# CMMLU 公开基准数据集质量审计报告

> 生成时间：2026-11-25 22:47:47  
> 审计目录：`data/raw/cmmlu`  
> 覆盖样本：**11,917** 条（`dev`: 335，`test`: 11,582）  
> 检出风险条目：**772** 条（占比 6.48%），累计触发规则 **797** 次，Schema 异常 **0** 项

## 一、缺陷分级与规则分布

| 严重级别 | 命中次数 | 说明 |
| :--- | ---: | :--- |
| critical | 13 | 冲突标准答案 / 重复选项 / 缺失必填字段 |
| high | 25 | 残缺图表上下文（瞎子题） / dev-test 精确或近似泄露 |
| medium | 662 | 康熙部首 OCR 污染 / LaTeX 语法断裂 / HTML 残留 / 跨题重复 |
| low | 97 | 题干过短或截断风险 |

| 规则编号 | 命中次数 |
| :--- | ---: |
| `CHK_KANGXI_OCR_ARTIFACT` | 552 |
| `CHK_EXACT_DUPLICATE_ITEM` | 102 |
| `CHK_TRUNCATED_STEM` | 97 |
| `CHK_CONFLICTING_GOLD_ANSWER` | 12 |
| `CHK_DEV_TEST_NEAR_LEAKAGE` | 12 |
| `CHK_DEV_TEST_LEAKAGE` | 8 |
| `CHK_LATEX_SYNTAX_BROKEN` | 8 |
| `CHK_MISSING_VISUAL_CONTEXT` | 5 |
| `CHK_DUPLICATE_OPTIONS` | 1 |

## 二、问题最集中学科排行（Test 集 Top 15）

| 学科 | 总题数 | 高危/致命题数 | 累计命中题数 | 最大单选项占比 |
| :--- | ---: | ---: | ---: | ---: |
| `ancient_chinese` | 164 | 11 | 15 | 26.2% |
| `sociology` | 226 | 6 | 13 | 25.2% |
| `high_school_mathematics` | 164 | 2 | 60 | 25.6% |
| `logical` | 123 | 2 | 8 | 25.2% |
| `education` | 163 | 2 | 5 | 25.2% |
| `chinese_teacher_qualification` | 179 | 2 | 2 | 25.1% |
| `college_mathematics` | 105 | 1 | 10 | 32.4% |
| `genetics` | 176 | 1 | 6 | 25.6% |
| `college_law` | 108 | 1 | 3 | 32.4% |
| `high_school_chemistry` | 132 | 1 | 2 | 25.0% |
| `machine_learning` | 122 | 1 | 2 | 25.4% |
| `nutrition` | 145 | 1 | 2 | 25.5% |
| `chinese_foreign_policy` | 107 | 1 | 1 | 25.2% |
| `conceptual_physics` | 147 | 1 | 1 | 25.2% |
| `computer_science` | 204 | 0 | 168 | 25.5% |

## 三、高置信真实缺陷样本摘录（供人工复核与模型 Bad Case 实测）

- **[CRITICAL] `dev/elementary_mathematics#1`** (`CHK_CONFLICTING_GOLD_ANSWER`): Identical question & options have conflicting gold answers across [dev/elementary_mathematics#1, test/high_school_mathematics#128]  
  题干摘录：`集合A={1，2,3, 4}的真⼦集个数为`
- **[CRITICAL] `test/education#114`** (`CHK_CONFLICTING_GOLD_ANSWER`): Identical question & options have conflicting gold answers across [test/education#114, test/education#131]  
  题干摘录：`决定教育性质的根本因素是`
- **[CRITICAL] `test/education#131`** (`CHK_CONFLICTING_GOLD_ANSWER`): Identical question & options have conflicting gold answers across [test/education#114, test/education#131]  
  题干摘录：`决定教育性质的根本因素是`
- **[CRITICAL] `test/high_school_mathematics#128`** (`CHK_CONFLICTING_GOLD_ANSWER`): Identical question & options have conflicting gold answers across [dev/elementary_mathematics#1, test/high_school_mathematics#128]  
  题干摘录：`集合A={1,2,3,4}的真⼦集个数为`
- **[CRITICAL] `test/logical#84`** (`CHK_CONFLICTING_GOLD_ANSWER`): Identical question & options have conflicting gold answers across [test/logical#84, test/logical#85]  
  题干摘录：`根据演绎有效性原则，论证无效的一个重要标志是`
- **[CRITICAL] `test/genetics#36`** (`CHK_DUPLICATE_OPTIONS`): Identical normalized options: A=C('1/16 ')  
  题干摘录：`豌豆中，高茎(T)对矮茎(t)为显性，黄子叶(Y)对绿子叶(y)为显性，假定这两个位点的遗传符合孟德尔第二定律，若把真实遗传的高茎黄子叶个体与矮茎绿子叶个体进行`
- **[HIGH] `dev/ancient_chinese#4`** (`CHK_DEV_TEST_LEAKAGE`): Exact dev/test split leakage across [dev/ancient_chinese#4, test/ancient_chinese#83] (sig=be25abc4d3e3966d)  
  题干摘录：`按照传统的“六书”体例，“益”字应属`
- **[HIGH] `dev/college_law#1`** (`CHK_DEV_TEST_LEAKAGE`): Exact dev/test split leakage across [dev/college_law#1, test/college_law#99] (sig=4ef9d5366d90c672)  
  题干摘录：`以下选项中，属于邻接权客体的是`
- **[HIGH] `dev/college_mathematics#1`** (`CHK_DEV_TEST_LEAKAGE`): Exact dev/test split leakage across [dev/college_mathematics#1, test/college_mathematics#6] (sig=60503b58c06f2ebd)  
  题干摘录：`函数 $f(x)=\frac{x-x^3}{\sin \pi x}$ 的可去间断点个数为.`
- **[HIGH] `dev/high_school_mathematics#2`** (`CHK_DEV_TEST_LEAKAGE`): Exact dev/test split leakage across [dev/high_school_mathematics#2, test/high_school_mathematics#159] (sig=0179e5e02a1921e8)  
  题干摘录：`已知⼀个等差数列的⾸项为1，公差为3，那么该数列的前5项和为`
- **[HIGH] `test/ancient_chinese#83`** (`CHK_DEV_TEST_LEAKAGE`): Exact dev/test split leakage across [dev/ancient_chinese#4, test/ancient_chinese#83] (sig=be25abc4d3e3966d)  
  题干摘录：`按照传统的”六书”体例，”益”字应属`
- **[HIGH] `test/ancient_chinese#126`** (`CHK_DEV_TEST_NEAR_LEAKAGE`): 3-gram Jaccard=1.000 (>= 0.85) with dev/ancient_chinese#1  
  题干摘录：`下列四组字中，全是会意字的一组是`
- **[HIGH] `test/ancient_chinese#148`** (`CHK_DEV_TEST_NEAR_LEAKAGE`): 3-gram Jaccard=1.000 (>= 0.85) with dev/ancient_chinese#1  
  题干摘录：`下列四组字中，全是会意字的一组是`
- **[HIGH] `test/ancient_chinese#158`** (`CHK_DEV_TEST_NEAR_LEAKAGE`): 3-gram Jaccard=1.000 (>= 0.85) with dev/ancient_chinese#0  
  题干摘录：`下列四组字中，全是形声字的一组是`
- **[HIGH] `test/ancient_chinese#32`** (`CHK_DEV_TEST_NEAR_LEAKAGE`): 3-gram Jaccard=1.000 (>= 0.85) with dev/ancient_chinese#1  
  题干摘录：`下列四组字中，全是会意字的一组是`
- **[HIGH] `test/ancient_chinese#40`** (`CHK_DEV_TEST_NEAR_LEAKAGE`): 3-gram Jaccard=1.000 (>= 0.85) with dev/ancient_chinese#0  
  题干摘录：`下列四组字中，全是形声字的一组是`
- **[HIGH] `test/chinese_foreign_policy#64`** (`CHK_MISSING_VISUAL_CONTEXT`): References missing figure/table ('下表所示') in text-only CSV  
  题干摘录：`下表所示为1956~1959年中国部分外交活动。中国政府坚决支持埃及人民收回苏伊士运河主权的正义斗争。中国除了给予柬埔寨经济援助外，还与尼泊尔、锡兰、缅甸、印尼等国签订经济援助的正式协定。中国先后与挪威、荷兰、南斯拉夫、阿富汗、尼泊尔、埃及`
- **[HIGH] `test/chinese_teacher_qualification#103`** (`CHK_MISSING_VISUAL_CONTEXT`): References missing figure/table ('以下图') in text-only CSV  
  题干摘录：`我国不同民族的室内装饰与居住环境各有恃色。以下图的民居室内装饰反映的民族特色是`
- **[HIGH] `test/chinese_teacher_qualification#160`** (`CHK_MISSING_VISUAL_CONTEXT`): References missing figure/table ('图三') in text-only CSV  
  题干摘录：`在Word中，单击“插入”选项卡下的“表格”按钮，然后选择“插入表格”命令，如图三所示，则`
- **[HIGH] `test/conceptual_physics#106`** (`CHK_MISSING_VISUAL_CONTEXT`): References missing figure/table ('如图所示') in text-only CSV  
  题干摘录：`如图所示湖中有一小船，有人用绳绕过岸上一定高度处的定滑轮拉湖上的船向岸边运动，设该人以匀速率v0收绳，绳长不变，湖水静止，则小船的运动是`
- **[HIGH] `test/nutrition#56`** (`CHK_MISSING_VISUAL_CONTEXT`): References missing figure/table ('表2002') in text-only CSV  
  题干摘录：`《食物成分表2002》中的食物编码有6位，前2位是`
- **[MEDIUM] `test/anatomy#100`** (`CHK_EXACT_DUPLICATE_ITEM`): Exact duplicate item across [test/anatomy#79, test/anatomy#100] (sig=7e3cbfa572c160ba)  
  题干摘录：`颞横回是`
- **[MEDIUM] `test/anatomy#107`** (`CHK_EXACT_DUPLICATE_ITEM`): Exact duplicate item across [test/anatomy#107, test/anatomy#142] (sig=f1039fdbd61763c7)  
  题干摘录：`右主支气管的特点是`
- **[MEDIUM] `test/anatomy#112`** (`CHK_EXACT_DUPLICATE_ITEM`): Exact duplicate item across [test/anatomy#87, test/anatomy#112] (sig=09e0a1f1a6ca3eff)  
  题干摘录：`穿经内囊膝的纤维束是`
- **[MEDIUM] `test/anatomy#127`** (`CHK_EXACT_DUPLICATE_ITEM`): Exact duplicate item across [test/anatomy#45, test/anatomy#127] (sig=c42149b80cbcf5b9)  
  题干摘录：`不属于骶丛的神经是`
- **[MEDIUM] `test/anatomy#128`** (`CHK_EXACT_DUPLICATE_ITEM`): Exact duplicate item across [test/anatomy#72, test/anatomy#128] (sig=f09bf0a783542123)  
  题干摘录：`支配三角肌的神经是`
- **[MEDIUM] `dev/computer_science#0`** (`CHK_KANGXI_OCR_ARTIFACT`): Contains 2 PDF-OCR Kangxi/CJK radical chars: ⼆⽹  
  题干摘录：`关系数据库中的数据逻辑结构是`
- **[MEDIUM] `dev/computer_science#1`** (`CHK_KANGXI_OCR_ARTIFACT`): Contains 1 PDF-OCR Kangxi/CJK radical chars: ⾯  
  题干摘录：`下⾯属于端系统之间的协议是`
- **[MEDIUM] `dev/computer_science#2`** (`CHK_KANGXI_OCR_ARTIFACT`): Contains 1 PDF-OCR Kangxi/CJK radical chars: ⽹  
  题干摘录：`下列选项中，不属于线性结构的是`
- **[MEDIUM] `dev/computer_science#3`** (`CHK_KANGXI_OCR_ARTIFACT`): Contains 1 PDF-OCR Kangxi/CJK radical chars: ⾼  
  题干摘录：`RAM代表的是`
- **[MEDIUM] `dev/elementary_mathematics#1`** (`CHK_KANGXI_OCR_ARTIFACT`): Contains 1 PDF-OCR Kangxi/CJK radical chars: ⼦  
  题干摘录：`集合A={1，2,3, 4}的真⼦集个数为`
- **[MEDIUM] `test/college_actuarial_science#24`** (`CHK_LATEX_SYNTAX_BROKEN`): Odd count of unescaped '$' (1) in question stem  
  题干摘录：`假设X服从[0，10]均匀分布，设中心死亡率为m_x，则m_$为( )。`
- **[MEDIUM] `test/college_actuarial_science#3`** (`CHK_LATEX_SYNTAX_BROKEN`): Odd count of unescaped '$' (5) in question stem  
  题干摘录：`原保险人自留该保单组合风险损失的方差为( )。(1)$\lambda \operatorname{Var}(X_I)$;(2)$\lambda \int_{-\infty}^M x^2 f(x) \mathrm{d} x$(3)$\lamb`
- **[MEDIUM] `test/college_actuarial_science#66`** (`CHK_LATEX_SYNTAX_BROKEN`): Odd count of unescaped '$' (5) in question stem  
  题干摘录：`设$S(x)=\frac{1}{1+x}$，则剩余寿命$T(y)$中位数为___$。`
- **[MEDIUM] `test/college_mathematics#11`** (`CHK_LATEX_SYNTAX_BROKEN`): Odd count of unescaped '$' (1) in question stem  
  题干摘录：`将一枚硬币独立的掷两次， 引进事件: $A_1={第一次出现正面}， A_2={第二次出现正面}， A_3={正、反面各出现一次}， A_4={出现两次正面}， 则事件`
- **[MEDIUM] `test/college_mathematics#31`** (`CHK_LATEX_SYNTAX_BROKEN`): Odd count of unescaped '$' (1) in question stem  
  题干摘录：`设A为n阶方阵，且|A|=0$，则 ( ) .`
