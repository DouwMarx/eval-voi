#!/usr/bin/env python3
"""Mine the system-card corpus for the AI safety evaluations labs actually run.

Usage
-----
    uv run python research/mine_system_cards.py            # from the repo root; defaults below
    uv run python research/mine_system_cards.py --top 60 --db /path/to/docs.sqlite --out-dir research

Inputs (read-only)
------------------
SQLite database of system cards / model cards / third-party evals
(default: $SYSTEM_CARD_DB, a private corpus not shipped with this repository). Only the
documents with safety_evals=1 are used; their extracted text lives at
latest_versions.text_path relative to the database's project root.

Outputs (written to --out-dir)
------------------------------
system_card_evals.json     full candidate table (every candidate that survived the
                           stoplist, with DF, publishers, per-domain DF, lift, tf-idf)
system_card_evals.md       top-N table with capability-vs-safety labels + a curated
                           shortlist of 10 safety evals spanning the five risk domains
system_card_snippets.json  up to 15 verbatim sentences per shortlisted eval (slug,
                           publisher) for downstream elicitation context

Method
------
1. Text is whitespace-normalised and end-of-line hyphenation is joined.
2. Candidates come from (a) a hand-curated SEED list of known evals with explicit
   case-sensitive regexes, and (b) three generic shape regexes: benchmark-suffix
   tokens (...Bench/bench/Arena/Eval/Suite/QA/Test), ALL-CAPS acronyms (3-10
   chars, >=3 letters) and CamelCase names. Surface forms are merged by a key
   that lower-cases and strips non-alphanumerics (LAB-Bench == LABBench).
3. Auto-extracted candidates pass three filters: an explicit STOPLIST (model
   names, org names, tech/ policy acronyms, statistics tests, generic words: see
   the comments on STOPLIST for the justification of each group), a regex
   filter for model/version-like tokens, and a "case dominance" filter that
   drops a token when its plain lower-case/capitalised spelling is at least as
   common in the corpus as the shouty spelling (this removes heading words such
   as SUMMARY, and common words such as PAIR/pair, without a hand list).
4. Per candidate: document frequency (DF), distinct publishers, per-risk-domain
   DF and lift (DF share in domain / base rate of domain), a tf-idf
   distinctiveness score (sum over docs of tf * log(N/df)), and a rank score
   DF * (1 + ln(n_publishers)) that rewards cross-publisher adoption.
5. Snippets are sentences containing the candidate; they are scored for
   informativeness (numbers, task/hour/agreement vocabulary, sane length, not
   a table row), de-duplicated (system cards recycle paragraphs), and picked
   round-robin across publishers so the top three are not all from one lab.

6. The SHORTLIST is hand-curated (not the top of the ranking): ten purpose-built
   safety evaluations with cross-publisher support, at least one per risk domain.
   General capability benchmarks that labs also cite (SWE-bench, HLE, GPQA, ...)
   are labelled "capability" in the table and excluded from the shortlist; LAB-Bench
   was left out for the same reason (a science benchmark used as a bio proxy).
   BBQ is the one single-publisher entry (Anthropic runs it in every card).

Stoplist justification (see STOP_GROUPS): model_names = the thing evaluated;
org_names = who evaluates; policy_terms = thresholds/frameworks (ASL-3, CCL);
tech_terms = software/ML/cyber acronyms that share the acronym shape (API, CVE,
RLHF) plus elicitation-harness terms (AutoNudge); stats_terms = statistical tests
caught by the "...Test" shape; generic_words = English/heading words and common
nouns that collide with eval names (mask, shade, pair, bloom) so that only the
seed's case-sensitive regex can count them.

Everything is deterministic: no randomness, all ties broken by explicit sort
keys. Dependencies: numpy, stdlib only. Runtime about 15 s.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

import os

import numpy as np

DEFAULT_DB = Path(os.environ.get("SYSTEM_CARD_DB", "system_card_db/docs.sqlite"))
DOMAINS = ["cbrn", "cyber", "loss_of_control", "harmful_manipulation", "societal_harm"]

# --------------------------------------------------------------------------------------
# Seeds: canonical display name -> list of case-sensitive regexes. Names that are also
# common words (MASK, SHADE, PAIR) get upper-case-only patterns.
# --------------------------------------------------------------------------------------
SEEDS: dict[str, list[str]] = {
    # ---- CBRN ----
    "WMDP": [r"\bWMDP\b"],
    "VCT": [r"\bVCT\b", r"Virology Capabilities Test"],
    "LAB-Bench": [r"\bLAB[\- ]?Bench\b", r"\bLab[\- ]?[Bb]ench\b"],
    "BioLP-bench": [r"\bBioLP[\- ]?[Bb]ench\b", r"\bBioLP\b"],
    "ProtocolQA": [r"\bProtocolQA\b"],
    "CloningScenarios": [r"\bCloning ?Scenarios\b"],
    "FigQA": [r"\bFigQA\b"],
    "SeqQA": [r"\bSeqQA\b"],
    "Tacit Knowledge": [r"\b[Tt]acit [Kk]nowledge\b"],
    "Long-form Virology": [r"\b[Ll]ong[\- ]form [Vv]irology\b"],
    "Multimodal Virology Troubleshooting": [r"\b[Mm]ultimodal [Vv]irology [Tt]roubleshooting\b"],
    "BioRisk": [r"\bBioRisk\b"],
    "ChemBench": [r"\bChemBench\b"],
    "MBCT": [r"\bMBCT\b", r"\bMolecular Biology Capabilities Test\b"],
    "HPCT": [r"\bHPCT\b", r"\bHuman Pathogen Capabilities Test\b"],
    "WCB": [r"\bWCB\b", r"\bWorld Class Bio\b"],
    "BioTIER": [r"\bBioTIER\b", r"\bBioTier\b"],
    "ABC Bench": [r"\bABC[\- ]?Bench\b"],
    "ReproBAIT": [r"\bReproBAIT\b"],
    "TroubleshootingBench": [r"\bTroubleshootingBench\b"],
    "BixBench": [r"\bBixBench\b"],
    "MMLU": [r"\bMMLU(?:-Pro)?\b"],
    "GPQA": [r"\bGPQA\b"],
    # ---- Cyber ----
    "Cybench": [r"\bCy[Bb]ench\b"],
    "CyberSecEval": [r"\bCyber[Ss]ec[Ee]val\b"],
    "CTF": [r"\bCTFs?\b"],
    "Cyber Range": [r"\b[Cc]yber [Rr]ange\b"],
    "CyberGym": [r"\bCyber ?Gym\b"],
    "InterCode-CTF": [r"\bInter[Cc]ode[\- ]?CTF\b"],
    "NYU CTF": [r"\bNYU[\- ]?CTF\b"],
    "picoCTF": [r"\bpicoCTF\b"],
    "HackTheBox": [r"\bHack ?[Tt]he ?[Bb]ox\b"],
    "BountyBench": [r"\bBounty[Bb]ench\b"],
    "CVE-Bench": [r"\bCVE[\- ]?[Bb]ench\b"],
    "SecBench": [r"\bSecBench\b"],
    "PwnBench": [r"\bPwnBench\b"],
    "AgentDojo": [r"\bAgentDojo\b"],
    "ExploitBench": [r"\bExploit[\- ]?Bench\b"],
    "ExploitGym": [r"\bExploit[\- ]?Gym\b"],
    "CyScenarioBench": [r"\bCy[Ss]cenario[Bb]ench\b"],
    "OSS-Fuzz": [r"\bOSS[\- ]?Fuzz\b"],
    "FrontierCyber": [r"\bFrontierCyber\b"],
    "HackerBench": [r"\bHacker[Bb]ench\b"],
    "The Last Ones (TLO)": [r"\bTLO\b", r"\bThe Last Ones\b"],
    "Agent Red Teaming (ART)": [r"\bART\b", r"\bAgent Red Teaming\b"],
    "Indirect Prompt Injection (IPI)": [r"\bIPI\b", r"\b[Ii]ndirect [Pp]rompt [Ii]njection\b"],
    "Binary Exploitation Benchmark": [r"\bBinary Exploitation Benchmark\b"],
    # ---- Loss of control / autonomy / alignment ----
    "HCAST": [r"\bHCAST\b"],
    "RE-Bench": [r"\bRE[\- ]?[Bb]ench\b"],
    "SHADE-Arena": [r"\bSHADE[\- ]?Arena\b", r"\bShade[\- ]?Arena\b", r"\bSHADE\b"],
    "Agentic Misalignment": [r"\b[Aa]gentic [Mm]isalignment\b"],
    "Petri": [r"\bPetri\b"],
    "Bloom": [r"\bBloom\b"],
    "Apollo": [r"\bApollo\b"],
    "METR": [r"\bMETR\b"],
    "ASIMOV": [r"\bASIMOV\b"],
    "SWE-bench": [r"\bSWE[\- ]?[Bb]ench\b"],
    "Terminal-Bench": [r"\bTerminal[\- ]?[Bb]ench\b"],
    "OSWorld": [r"\bOSWorld\b"],
    "PaperBench": [r"\bPaperBench\b"],
    "MLE-bench": [r"\bMLE[\- ]?[Bb]ench\b"],
    "SWE-Lancer": [r"\bSWE[\- ]?Lancer\b"],
    "Vending-Bench": [r"\bVending[\- ]?[Bb]ench\b"],
    "Humanity's Last Exam": [r"\bHumanity.s [Ll]ast [Ee]xam\b", r"\bHLE\b"],
    "FrontierMath": [r"\bFrontierMath\b"],
    "ARC-AGI": [r"\bARC[\- ]?AGI\b"],
    "AIME": [r"\bAIME\b"],
    "BrowseComp": [r"\bBrowseComp\b"],
    "SimpleQA": [r"\bSimpleQA\b"],
    "GAIA": [r"\bGAIA\b"],
    "tau-bench": [r"\b(?:tau|τ|Tau|t)[\- ]?[Bb]ench\b", r"\btbench\b"],
    "Sandbagging": [r"\b[Ss]andbagging\b"],
    "Sycophancy": [r"\b[Ss]ycophancy\b"],
    "Alignment Faking": [r"\b[Aa]lignment [Ff]aking\b"],
    "Reward Hacking": [r"\b[Rr]eward [Hh]acking\b"],
    "Automated Researcher": [r"\b[Aa]utomated [Rr]esearcher\b"],
    "Cloud Run Elicitation": [r"\bCloud Run Elicitation\b"],
    "ControlArena": [r"\bControl[\- ]?[Aa][Rr][Ee][Nn][Aa]\b"],
    "SHUSHCAST": [r"\bSHUSHCAST\b"],
    "APPS Backdoors": [r"\bAPPS Backdoors?\b"],
    "Minimal-LinuxBench": [r"\b(?:Minimal[\- ])?LinuxBench\b"],
    "Epoch Capabilities Index (ECI)": [r"\bA?ECI\b", r"\bEpoch Capabilities Index\b"],
    "CoBench": [r"\bCoBench\b"],
    "PostTrainBench": [r"\bPostTrainBench\b"],
    "GDPval": [r"\bGDP[Vv]al\b"],
    "HealthBench": [r"\bHealth[\- ]?Bench\b"],
    # ---- Honesty / manipulation ----
    "MASK": [r"\bMASK\b"],
    "TruthfulQA": [r"\bTruthfulQA\b"],
    "MakeMePay": [r"\bMakeMePay\b"],
    "MakeMeSay": [r"\bMakeMeSay\b"],
    "Persuasion": [r"\bChangeMyView\b", r"\bPersuasion ?Bench\b"],
    # ---- Societal harm / harmful content ----
    "HarmBench": [r"\bHarm[Bb]ench\b"],
    "StrongREJECT": [r"\b[Ss]trongREJECT\b", r"\bStrongReject\b"],
    "AgentHarm": [r"\bAgent[Hh]arm\b"],
    "BBQ": [r"\bBBQ\b(?![ -](?:thermometer|grill|sauce|pit|smoker))"],
    "XSTest": [r"\bXSTest\b", r"\bXSTEST\b"],
    "ToxiGen": [r"\bToxi[Gg]en\b"],
    "RealToxicityPrompts": [r"\bRealToxicityPrompts\b"],
    "WildChat": [r"\bWildChat\b"],
    "WildJailbreak": [r"\bWildJailbreak\b"],
    "JailbreakBench": [r"\bJailbreak[Bb]ench\b"],
    "SORRY-Bench": [r"\bSORRY[\- ]?[Bb]ench\b"],
    "Do-Not-Answer": [r"\bDo[\- ]Not[\- ]Answer\b"],
    "AILuminate": [r"\bAILuminate\b"],
    "FORTRESS": [r"\bFORTRESS\b"],
    "Gray Swan Arena": [r"\bGray ?Swan ?Arena\b"],
    "AgentBench": [r"\bAgentBench\b"],
    "AIR-Bench": [r"\bAIR[\- ]?[Bb]ench\b"],
    "SafetyBench": [r"\bSafetyBench\b"],
    "SycophancyEval": [r"\bSycophancyEval\b"],
    "Model Spec": [r"\bModel Spec\b"],
}

# --------------------------------------------------------------------------------------
# Stoplist (normalised keys: lower-case, alphanumerics only). Grouped by the reason
# each group is not an evaluation. Applied to auto-extracted candidates only.
# --------------------------------------------------------------------------------------
STOP_GROUPS: dict[str, list[str]] = {
    # Model / product names: the thing being evaluated, not an evaluation.
    "model_names": [
        "gpt", "chatgpt", "claude", "gemini", "gemma", "llama", "grok", "qwen", "deepseek",
        "mistral", "mixtral", "opus", "sonnet", "haiku", "mythos", "fable", "codex", "gpt4o",
        "gpt4", "gpt5", "gpt45", "gpto", "davinci", "palm", "bard", "phi", "nemotron", "kimi",
        "glm", "minimax", "yi", "vllm", "sglang", "ollama", "openrouter", "copilot", "cursor",
        "veo", "imagen", "sora", "dalle", "whisper", "chatgptagent", "computeruse", "agentsdk",
        "opusthinking", "gptoss", "llamaguard", "promptguard", "codeshield", "shieldgemma",
        "gpt5codex", "gpt5pro", "gemini3", "gemini25", "gemini25pro", "claudecode", "claudeai",
        "gpt5chat", "gpt5thinking", "gptrealtime", "gpt5mini", "gpt5nano", "gemini3pro",
        "deepthink", "gpt51", "gpt52", "gpt53", "gpt4omini", "gpt4turbo", "gemini15",
        "gemini20", "gemini31", "gemini31pro", "mythospreview", "opus4", "sonnet4", "haiku45",
        "sonnet45", "opus45", "opus46", "opus47", "opus48", "sonnet5", "fable5", "mythos5",
        "geminipro", "geminiultra", "geminiflash", "geminiapp", "gemini3deepthink",
        "aistudio", "vertexai", "googleai", "amazonbedrock", "sagemaker",
    ],
    # Organisations, teams and programmes: publishers or evaluators, not evaluations.
    # METR and Apollo are seeded on purpose (task spec) and are labelled as orgs in the table.
    "org_names": [
        "openai", "anthropic", "deepmind", "googledeepmind", "google", "meta", "xai", "nvidia",
        "microsoft", "amazon", "aws", "azure", "apple", "alibaba", "baidu", "tencent",
        "bytedance", "huggingface", "github", "gitlab", "stackoverflow", "reddit", "twitter",
        "youtube", "linkedin", "wikipedia", "arxiv", "aisi", "ukaisi", "usaisi", "caisi",
        "uscaisi", "nist", "rand", "securebio", "redwood", "redwoodresearch", "transluce",
        "farai", "epochai", "epoch", "palisade", "palisaderesearch", "saferai", "mlcommons",
        "mitre", "owasp", "darpa", "iarpa", "nsa", "cia", "fbi", "doe", "dod", "dhs", "cisa",
        "nih", "who", "cdc", "fda", "epa", "unesco", "oecd", "nato", "eu", "un", "uk", "us",
        "usa", "usg", "ieee", "acm", "mit", "ucb", "ucl", "cmu", "nyu", "stanford", "harvard",
        "oxford", "cambridge", "berkeley", "deepseekai", "moonshot", "zhipu", "zai", "inclusionai",
        "thinkingmachines", "scaleai", "surgeai", "mercor", "hackerone", "bugcrowd", "cais",
        "fli", "fhi", "govai", "ftc", "sec", "doj", "cnas", "csis", "brookings", "cset",
        "arc", "arcevals", "alignmentresearchcenter", "opp", "openphil", "graysw", "grayswan",
        "haize", "haizelabs", "lakera", "robustintelligence", "leap", "leaplabs", "frontiermodelforum",
        "fmf", "pai", "partnershiponai", "cset", "ipcc", "iaea", "opcw", "bwc", "cwc",
        "gdm", "gpai", "cern", "wmd", "wmdc", "wmda", "apollo research", "cnss", "futurehouse",
        "latchbio", "spacexai", "crowdstrike", "lesswrong", "irregular", "andonlabs", "andon",
        "databricks", "mcdiarmid", "macdiarmid", "mccarthy", "xiaomi", "mimo", "sekai", "glacier",
        "hkcert", "csaw", "defcon", "blackhat",
    ],
    # Frontier-safety policy vocabulary: thresholds and frameworks, not evaluations.
    "policy_terms": [
        "asl", "asl1", "asl2", "asl3", "asl4", "asl5", "rsp", "fsf", "ccl", "ccls", "osp", "ssp",
        "sl", "kcl", "kcls", "cbrn", "cbrne", "cbrnw", "cb", "rn", "hlmi", "agi", "asi", "tai",
        "pf", "psf", "frontiersafetyframework", "responsiblescalingpolicy", "preparedness",
        "preparednessframework", "sag", "safetyadvisorygroup", "dsb", "lts", "ltbt", "rse",
        "aisafetylevel", "criticalcapabilitylevel", "capabilitythreshold", "safetycase",
        "highcapability", "criticalcapability", "trackedcategory", "alertthreshold",
        "spec", "modelspec", "eu", "euaiact", "aiact", "nda", "sla", "tos", "toc", "sop", "sops",
    ],
    # Generic technical / ML / software acronyms and names.
    "tech_terms": [
        "ace", "nla", "nlas", "hawk", "oss", "autonudge", "graphwalks", "needles", "captcha", "aav", "cad", "gdp", "spidermonkey", "csam",
        "pdfs", "webassembly", "iso", "cpus", "pdb", "readme", "ssrf", "blast", "esm", "esm2",
        "nanogpt", "ics", "iec", "alphafold", "aes", "zdr", "smiles", "sqlite", "iupac", "php",
        "aslr", "iou", "hdf5", "uuid", "llc", "phds", "rss", "rms", "pid", "ffmpeg", "yearold",
        "synthid", "att", "attck", "react", "openclaw", "opencode", "litellm", "mts", "cobol",
        "fortran", "rust", "golang", "cpp", "npm", "pip", "conda", "cmake", "bash", "zsh", "fish",
        "html5", "css3", "es6", "jsx", "tsx", "yml", "toml", "ini", "cfg", "env", "dotenv",
        "gitpod", "codespaces", "heroku", "vercel", "netlify", "cloudflare", "akamai", "fastly",
        "ai", "ais", "ml", "llm", "llms", "nlp", "api", "apis", "sdk", "cli", "gui", "ui", "ux",
        "os", "cpu", "gpu", "gpus", "tpu", "tpus", "ram", "vram", "ssd", "hdd", "http", "https",
        "url", "urls", "html", "css", "csv", "json", "yaml", "xml", "sql", "pdf", "png", "jpg",
        "jpeg", "gif", "svg", "mp4", "txt", "md", "ssh", "tls", "ssl", "dns", "vpn", "ip", "tcp",
        "udp", "ftp", "smtp", "imap", "vm", "vms", "ide", "ides", "rl", "rlhf", "rlaif", "sft",
        "dpo", "ppo", "grpo", "cot", "cots", "kv", "moe", "lora", "qlora", "peft", "rag", "mcp",
        "a2a", "tts", "asr", "ocr", "cv", "nn", "cnn", "rnn", "lstm", "gan", "vae", "vlm", "vlms",
        "mllm", "vla", "sota", "ood", "iid", "auc", "roc", "auroc", "f1", "mse", "rmse", "mae",
        "elo", "elos", "mcq", "mcqs", "qa", "qas", "mb", "gb", "kb", "tb", "ms", "hz", "khz", "ghz",
        "fps", "usd", "eur", "gbp", "cny", "jsonl", "regex", "utf8", "ascii", "unicode", "ansi",
        "posix", "unix", "linux", "windows", "macos", "ios", "android", "python", "javascript",
        "typescript", "pytorch", "tensorflow", "jax", "numpy", "scipy", "cuda", "nvlink", "pcie",
        "infiniband", "kubernetes", "docker", "aws", "gcp", "ec2", "s3", "iam", "sso", "oauth",
        "saml", "jwt", "csrf", "xss", "sqli", "rce", "dos", "ddos", "lpe", "poc", "cve", "cves",
        "cwe", "cwes", "cvss", "ioc", "iocs", "soc", "siem", "edr", "ttp", "ttps", "c2", "apt",
        "apts", "mitm", "waf", "ids", "ips", "nids", "av", "pii", "phi", "gdpr", "ccpa", "hipaa",
        "kyc", "aml", "faq", "faqs", "tldr", "tbd", "todo", "wip", "eta", "fyi", "imo", "iirc",
        "afaik", "asap", "na", "nb", "ps", "ok", "okay", "ceo", "cto", "cfo", "coo", "ciso", "vp",
        "svp", "phd", "md", "ba", "bs", "ms", "msc", "bsc", "jd", "mba", "utc", "est", "pst",
        "pdt", "edt", "gmt", "cet", "bst", "q1", "q2", "q3", "q4", "fy", "fy24", "fy25", "fy26",
        "ibm", "intel", "amd", "arm", "risc", "riscv", "x86", "gpt2", "bert", "t5", "clip",
        "resnet", "vit", "diffusion", "stem", "mooc", "wifi", "bluetooth", "iot", "ar", "vr",
        "xr", "led", "lcd", "oled", "hdmi", "usb", "sms", "mms", "gps", "lidar", "radar", "sonar",
        "dna", "rna", "mrna", "pcr", "crispr", "elisa", "ppe", "bsl", "bsl3", "bsl4", "sars",
        "sarscov2", "covid", "covid19", "hiv", "aids", "tb", "ttx", "lsd", "thc", "cbd",
        "openapi", "restapi", "graphql", "grpc", "websocket", "webhook", "cdn", "dom", "seo",
        "crm", "erp", "saas", "paas", "iaas", "b2b", "b2c", "roi", "kpi", "kpis", "okr", "okrs",
        "swe", "swes", "mle", "mles", "sre", "devops", "qa", "ci", "cd", "cicd", "pr", "prs",
        "loc", "sloc", "lto", "jit", "gc", "abi", "isa", "asm", "llvm", "gcc", "clang", "gdb",
        "binaryninja", "ghidra", "ida", "burpsuite", "burp", "nmap", "metasploit", "wireshark",
        "kali", "ubuntu", "debian", "centos", "rhel", "fedora", "archlinux", "nixos",
        "pytest", "unittest", "jest", "mocha", "junit", "selenium", "playwright", "puppeteer",
        "chatbotarena", "lmarena", "lmsys",  # human-preference leaderboards: capability, keep out of safety table
        "colab", "jupyter", "notebook", "vscode", "vim", "emacs", "excel", "powerpoint", "word",
        "sheets", "docs", "slides", "gmail", "outlook", "slack", "discord", "zoom", "teams",
        "webarena", "visualwebarena",  # web-agent capability benchmarks (kept as auto candidates if shape matches, but labelled)
    ],
    # Statistics vocabulary caught by the "...Test" / CamelCase shapes.
    "stats_terms": [
        "ttest", "ztest", "ftest", "chisquaretest", "chisquare", "wilcoxontest", "mannwhitneytest",
        "mannwhitney", "kruskalwallis", "kolmogorovsmirnov", "shapirowilk", "fishersexacttest",
        "permutationtest", "bootstraptest", "logranktest", "likelihoodratiotest", "waldtest",
        "hypothesistest", "significancetest", "binomialtest", "mcnemartest", "bonferroni",
        "abtest", "abtests", "unittest", "unittests", "integrationtest", "regressiontest",
        "stresstest", "stresstests", "penetrationtest", "pentest", "pentests", "smoketest",
        "irt", "cis", "ci", "cds", "ttest", "pvalue", "anova",
        "loadtest", "fuzztest", "posttest", "pretest", "retest", "selftest", "backtest",
    ],
    # Generic English words and heading words that survive the shape regexes.
    "generic_words": [
        "bench", "arena", "eval", "evals", "suite", "test", "tests", "qa", "benchmark",
        "benchmarks", "thetest", "atest", "note", "notes", "summary", "introduction",
        "appendix", "abstract", "conclusion", "conclusions", "figure", "table", "section",
        "chapter", "part", "page", "contents", "references", "acknowledgements",
        "acknowledgments", "warning", "caution", "important", "example", "examples",
        "yes", "no", "true", "false", "none", "null", "all", "any", "new", "old", "the", "and",
        "for", "not", "but", "with", "from", "this", "that", "are", "was", "were", "has", "have",
        "had", "can", "may", "will", "would", "should", "could", "must", "shall", "than", "then",
        "when", "where", "what", "which", "who", "why", "how", "our", "your", "their", "its",
        "his", "her", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
        "ten", "high", "low", "medium", "critical", "level", "levels", "risk", "risks", "safe",
        "safety", "harm", "harms", "model", "models", "system", "systems", "card", "cards",
        "report", "reports", "result", "results", "score", "scores", "task", "tasks", "prompt",
        "prompts", "agent", "agents", "tool", "tools", "user", "users", "data", "dataset",
        "datasets", "human", "humans", "expert", "experts", "baseline", "baselines", "release",
        "public", "private", "internal", "external", "draft", "final", "version", "update",
        "unknown", "other", "others", "total", "overall", "average", "mean", "median", "max",
        "min", "top", "bottom", "left", "right", "up", "down", "pass", "fail", "passed", "failed",
        "done", "end", "start", "stop", "run", "runs", "step", "steps", "trial", "trials",
        "round", "rounds", "phase", "phases", "turn", "turns", "goal", "goals", "plan", "plans",
        "mode", "modes", "type", "types", "class", "classes", "case", "cases", "item", "items",
        "list", "lists", "set", "sets", "group", "groups", "team", "teams", "member", "members",
        "staff", "board", "office", "policy", "policies", "law", "laws", "act", "acts", "rule",
        "rules", "code", "codes", "file", "files", "line", "lines", "row", "rows", "column",
        "columns", "cell", "cells", "key", "keys", "value", "values", "field", "fields",
        "input", "inputs", "output", "outputs", "error", "errors", "bug", "bugs", "fix",
        "fixes", "patch", "patches", "flag", "flags", "option", "options", "default", "custom",
        "auto", "manual", "open", "closed", "read", "write", "edit", "delete", "add", "remove",
        "id", "ids", "name", "names", "title", "titles", "date", "dates", "time", "times", "day",
        "days", "week", "weeks", "month", "months", "year", "years", "hour", "hours", "minute",
        "minutes", "second", "seconds", "pdfpage", "changelog", "executivesummary",
        "helpful", "harmless", "honest", "hhh", "pair", "pairs", "shade", "shades", "mask", "masks",
        "bloom", "blooms", "petri", "apollo", "arc", "gaia", "bbq", "vct", "hle", "swe", "ctf",
        # Journal / venue acronyms.
        "neurips", "icml", "iclr", "acl", "emnlp", "naacl", "cvpr", "iccv", "eccv", "aaai",
        "ijcai", "kdd", "www", "chi", "uist", "ccs", "usenix", "ndss", "sp", "pnas", "nature",
        "science", "jama", "bmj", "lancet", "cell", "plos", "elife", "bioarxiv", "biorxiv",
        "medrxiv", "ssrn", "doi", "isbn", "issn", "orcid",
        # Country / region codes and currencies that pass the acronym shape.
        "usa", "uk", "eu", "prc", "cn", "jp", "kr", "de", "fr", "ca", "au", "nz", "in", "ru",
        "ir", "il", "sa", "ae", "sg", "hk", "tw", "br", "mx", "za", "ng", "eg", "ke",
        "usd", "eur", "gbp", "jpy", "cny", "rmb", "btc", "eth",
        # Bio / chem entities frequently in ALL CAPS in CBRN sections.
        "atp", "adp", "nad", "nadh", "gtp", "ldh", "ldl", "hdl", "igg", "igm", "iga", "ige",
        "mrsa", "ebola", "marburg", "anthrax", "botulinum", "ricin", "sarin", "vx", "tabun",
        "soman", "novichok", "mers", "h5n1", "h1n1", "h7n9", "hpai", "lpai", "smallpox",
        "variola", "monkeypox", "mpox", "plague", "yersinia", "tularemia", "brucella",
        "coxiella", "chikungunya", "zika", "dengue", "nipah", "hendra", "lassa", "junin",
        "machupo", "cchf", "rvf", "vee", "eee", "wee", "sle", "je", "tbe", "kfd", "omsk",
        "hantaan", "sin nombre", "seoul", "puumala", "dobrava", "andes", "hps", "hfrs", "sars",
        "mers-cov", "hcov", "rsv", "hmpv", "hpiv", "adenovirus", "rhinovirus", "enterovirus",
        "poliovirus", "polio", "measles", "mumps", "rubella", "varicella", "vzv", "hsv", "cmv",
        "ebv", "hhv", "hbv", "hcv", "hdv", "hev", "hav", "hpv", "htlv", "jcv", "bkv", "b19",
    ],
}
STOPLIST: set[str] = {w for grp in STOP_GROUPS.values() for w in grp}

# Tokens that look like model versions / hardware SKUs rather than evals.
MODEL_LIKE_RE = re.compile(
    r"^(?:gpt|o[1-9]|claude|gemini|gemma|llama|grok|qwen|deepseek|mistral|mixtral|opus|sonnet|"
    r"haiku|mythos|fable|codex|phi|nemotron|kimi|glm|minimax|h100|h200|b200|a100|gb200|gb300|"
    r"tpu|v[1-9]|r[1-9]|k[1-9]|m[1-9]|x[1-9]|s[1-9]|dgx|hgx|rtx|xeon|epyc)(?:[a-z0-9]*)$"
)

# --------------------------------------------------------------------------------------
# Shape regexes (case-sensitive) for auto-extraction.
# --------------------------------------------------------------------------------------
SUFFIX_RE = re.compile(
    r"\b([A-Za-z][A-Za-z0-9]*(?:[\-\s][A-Za-z0-9]+)?[\-\s]?(?:Bench|bench|Arena|Eval|Evals|Suite|QA|Test))\b"
)
SPACED_SUFFIX_RE = re.compile(r"\b([A-Z][A-Za-z0-9\-]+ (?:Bench|Arena))\b")
ACRONYM_RE = re.compile(r"\b([A-Z][A-Z0-9]*(?:-[A-Z0-9]+)?)\b")
CAMEL_RE = re.compile(r"\b([A-Z][a-z0-9]+[A-Z][A-Za-z0-9]*|[A-Z]{2,}[a-z][A-Za-z0-9]*)\b")
SUFFIX_WORDS = {"Bench", "bench", "Arena", "Eval", "Evals", "Suite", "QA", "Test"}
WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9\-]*")
SENT_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9“\"(\[])")


def norm_key(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def normalise_text(raw: str) -> str:
    t = raw.replace("­", "")
    t = re.sub(r"(\w)-\n\s*(\w)", r"\1-\2", t)  # keep explicit hyphens across line breaks
    t = re.sub(r"[​‌‍﻿]", "", t)
    t = re.sub(r"\s+", " ", t)
    return t.strip()


# --------------------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------------------
def load_docs(db_path: Path) -> list[dict]:
    root = db_path.parent.parent
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    rows = con.execute(
        "SELECT d.slug, d.title, d.publisher, d.doc_type, d.publication_date, d.risk_domains, "
        "l.text_path FROM documents d JOIN latest_versions l ON l.document_id = d.id "
        "WHERE d.safety_evals = 1 AND l.text_path IS NOT NULL ORDER BY d.slug"
    ).fetchall()
    con.close()
    docs = []
    for slug, title, pub, dtype, date, rd, tpath in rows:
        p = root / tpath
        if not p.exists():
            continue
        text = normalise_text(p.read_text(encoding="utf-8", errors="replace"))
        docs.append(
            {
                "slug": slug,
                "title": title,
                "publisher": pub,
                "doc_type": dtype,
                "date": date,
                "domains": sorted(json.loads(rd) if rd else []),
                "text": text,
                "n_words": len(WORD_RE.findall(text)),
            }
        )
    return docs


# --------------------------------------------------------------------------------------
# Candidate extraction
# --------------------------------------------------------------------------------------
def extract_candidates(docs: list[dict]):
    """Return (per_doc_spans, surface_forms, word_counter).

    per_doc_spans[key][doc_idx] = set of match start offsets
    surface_forms[key] = Counter of surface strings
    word_counter = Counter of all case-sensitive word tokens in the corpus
    """
    seed_patterns = [(name, re.compile(p)) for name, pats in SEEDS.items() for p in pats]
    seed_keys = {name: norm_key(name) for name in SEEDS}
    seed_key_set = set(seed_keys.values())
    per_doc: dict[str, dict[int, set[int]]] = defaultdict(lambda: defaultdict(set))
    surface: dict[str, Counter] = defaultdict(Counter)
    is_seed: dict[str, bool] = {}
    word_counter: Counter = Counter()

    for i, d in enumerate(docs):
        t = d["text"]
        word_counter.update(WORD_RE.findall(t))
        covered = np.zeros(len(t) + 1, dtype=bool)  # chars claimed by a seed match
        for name, pat in seed_patterns:
            k = seed_keys[name]
            is_seed[k] = True
            for m in pat.finditer(t):
                per_doc[k][i].add(m.start())
                surface[k][name] += 1
                covered[m.start():m.end()] = True
        for rx in (SUFFIX_RE, SPACED_SUFFIX_RE, ACRONYM_RE, CAMEL_RE):
            for m in rx.finditer(t):
                s = m.group(1).strip()
                if rx is ACRONYM_RE:
                    letters = sum(ch.isalpha() for ch in s)
                    if not (3 <= len(s) <= 10 and letters >= 3):
                        continue
                if rx is SUFFIX_RE and s in SUFFIX_WORDS:
                    continue
                if rx is SUFFIX_RE and " " in s:
                    # only accept spaced forms handled by SPACED_SUFFIX_RE (Bench/Arena)
                    continue
                k = norm_key(s)
                if not k or len(k) < 3:
                    continue
                if covered[m.start()] or k in seed_key_set:
                    # Inside a seed match (e.g. "LinuxBench" inside "Minimal-LinuxBench"), or a
                    # seed's key: seed regexes are authoritative (they carry case and context
                    # guards such as BBQ-not-thermometer), so auto matches must not merge in.
                    continue
                per_doc[k][i].add(m.start())
                surface[k][s] += 1
                is_seed.setdefault(k, False)
    return per_doc, surface, is_seed, word_counter


def passes_filters(key: str, forms: Counter, word_counter: Counter) -> tuple[bool, str]:
    if key in STOPLIST:
        return False, "stoplist"
    if MODEL_LIKE_RE.match(key):
        return False, "model_like"
    if re.fullmatch(r"[a-z]*\d+[a-z0-9]*", key) and sum(c.isalpha() for c in key) < 3:
        return False, "sku_like"
    # Case-dominance: the shouty spelling must beat the plain spelling in the corpus.
    top_form = forms.most_common(1)[0][0]
    plain = {top_form.lower(), top_form.capitalize()} - {top_form}
    plain_count = sum(word_counter.get(p, 0) for p in plain)
    if plain_count >= word_counter.get(top_form, 0):
        return False, "case_dominance"
    return True, ""


# --------------------------------------------------------------------------------------
# Statistics
# --------------------------------------------------------------------------------------
def compute_table(docs, per_doc, surface, is_seed, word_counter):
    N = len(docs)
    keys = sorted(per_doc)
    keep, dropped = [], Counter()
    for k in keys:
        if is_seed.get(k):
            keep.append(k)
            continue
        ok, why = passes_filters(k, surface[k], word_counter)
        if ok:
            keep.append(k)
        else:
            dropped[why] += 1
    M = np.zeros((len(keep), N), dtype=np.int64)
    for r, k in enumerate(keep):
        for i, spans in per_doc[k].items():
            M[r, i] = len(spans)
    present = M > 0
    df = present.sum(axis=1)
    doc_len = np.array([max(d["n_words"], 1) for d in docs], dtype=np.float64)
    idf = np.log(N / np.maximum(df, 1))
    tf = M / doc_len[None, :]
    tfidf = (tf * idf[:, None]).sum(axis=1) * 1e4  # scaled for readability

    pubs = [d["publisher"] for d in docs]
    dom_mask = {dom: np.array([dom in d["domains"] for d in docs]) for dom in DOMAINS}
    # Domain attribution: only docs tagged with 1-3 domains carry information about
    # which domain an eval belongs to (the big system cards are tagged with all five).
    # Such a doc gives weight 1/k to each of its k domains. Lift is smoothed with one
    # pseudo-doc drawn from the base distribution so a single mention cannot dominate.
    dom_w = {
        dom: np.array(
            [(1.0 / len(d["domains"])) if (dom in d["domains"] and len(d["domains"]) <= 3) else 0.0
             for d in docs]
        )
        for dom in DOMAINS
    }
    dom_base = {dom: dom_w[dom].sum() / sum(w.sum() for w in dom_w.values()) for dom in DOMAINS}
    ALPHA = 1.0

    rows = []
    for r, k in enumerate(keep):
        pub_set = sorted({pubs[i] for i in np.flatnonzero(present[r])})
        dom_df = {dom: int((present[r] & dom_mask[dom]).sum()) for dom in DOMAINS}
        wsum = {dom: float((present[r] * dom_w[dom]).sum()) for dom in DOMAINS}
        wtot = sum(wsum.values())
        dom_lift = {
            dom: round(((wsum[dom] + ALPHA * dom_base[dom]) / (wtot + ALPHA)) / dom_base[dom], 3)
            for dom in DOMAINS
        }
        top_dom = (
            max(DOMAINS, key=lambda dm: (dom_lift[dm], dom_df[dm], -DOMAINS.index(dm)))
            if wtot > 0 else "unresolved"
        )
        display = surface[k].most_common(1)[0][0] if not is_seed.get(k) else next(
            n for n in SEEDS if norm_key(n) == k
        )
        rows.append(
            {
                "name": display,
                "key": k,
                "seed": bool(is_seed.get(k)),
                "forms": dict(sorted(surface[k].items(), key=lambda kv: (-kv[1], kv[0]))[:6]),
                "df": int(df[r]),
                "total_mentions": int(M[r].sum()),
                "n_publishers": len(pub_set),
                "publishers": pub_set,
                "domain_df": dom_df,
                "domain_lift": dom_lift,
                "top_domain": top_dom,
                "tfidf": round(float(tfidf[r]), 4),
                "rank_score": round(float(df[r] * (1.0 + math.log(max(len(pub_set), 1)))), 3),
                "docs": sorted(docs[i]["slug"] for i in np.flatnonzero(present[r])) if df[r] >= 2 else [],
            }
        )
    rows.sort(key=lambda x: (-x["rank_score"], -x["df"], -x["tfidf"], x["name"]))
    return rows, dropped


# --------------------------------------------------------------------------------------
# Labels for the top table (capability vs safety). Assigned by hand after reading the
# corpus; anything not listed gets "unlabelled" so gaps are visible.
# --------------------------------------------------------------------------------------
LABELS: dict[str, tuple[str, str]] = {
    "metr": ("org", "third-party evaluator (METR), seeded per spec"),
    "apollo": ("org", "third-party evaluator (Apollo Research), seeded per spec"),
    "ctf": ("safety", "capture-the-flag cyber tasks used as offensive-cyber uplift measure"),
    "swebench": ("capability", "software engineering task benchmark"),
    "sycophancy": ("safety", "alignment property: telling users what they want to hear"),
    "labbench": ("safety", "biology lab protocol / literature tasks used as bio-uplift proxy"),
    "vct": ("safety", "virology troubleshooting test built for biorisk measurement"),
    "cyberrange": ("safety", "multi-stage network attack simulations for cyber uplift"),
    "shadearena": ("safety", "hidden-sabotage agent tasks with monitor"),
    "sandbagging": ("safety", "strategic under-performance on dangerous-capability evals"),
    "terminalbench": ("capability", "terminal / command-line agent task benchmark"),
    "mask": ("safety", "honesty under pressure: stated belief vs. statement"),
    "aime": ("capability", "competition maths"),
    "gpqa": ("capability", "graduate-level science QA; sometimes CBRN proxy"),
    "mmlu": ("capability", "broad knowledge multiple choice"),
    "protocolqa": ("safety", "lab protocol error-correction, bio-uplift proxy"),
    "rewardhacking": ("safety", "exploiting graders / environments instead of solving task"),
    "humanityslastexam": ("capability", "frontier academic knowledge exam"),
    "wmdp": ("safety", "hazardous bio/cyber/chem knowledge multiple choice"),
    "cybench": ("safety", "professional CTF challenges for cyber uplift"),
    "petri": ("safety", "automated auditing agent for misaligned behaviours"),
    "osworld": ("capability", "computer-use agent benchmark"),
    "agenticmisalignment": ("safety", "blackmail / harmful insider-action scenarios"),
    "strongreject": ("safety", "jailbreak robustness on forbidden prompts"),
    "bbq": ("safety", "social bias in question answering"),
    "bloom": ("safety", "automated behavioural evaluation generator (Anthropic)"),
    "browsecomp": ("capability", "web browsing agent benchmark"),
    "tacitknowledge": ("safety", "unpublished wet-lab know-how questions, bio-uplift"),
    "rebench": ("safety", "AI R&D automation tasks, autonomy threshold"),
    "alignmentfaking": ("safety", "complying in training to preserve values"),
    "vendingbench": ("capability", "long-horizon business simulation"),
    "hcast": ("safety", "human-calibrated autonomy tasks for time-horizon estimate"),
    "simpleqa": ("capability", "factual recall / hallucination rate"),
    "fortress": ("safety", "adversarial harmful-request suite with refusal balance"),
    "arcagi": ("capability", "abstract reasoning puzzles"),
    "harmbench": ("safety", "standardised harmful-behaviour red-teaming"),
    "cyberseceval": ("safety", "insecure code and cyber-attack helpfulness suite"),
    "gaia": ("capability", "general assistant tasks"),
    "multimodalvirologytroubleshooting": ("safety", "image-based virology troubleshooting (bio uplift)"),
    "longformvirology": ("safety", "open-ended virology protocol writing (bio uplift)"),
    "agentharm": ("safety", "harmful agentic task compliance"),
    "automatedresearcher": ("safety", "AI R&D autonomy threshold experiments"),
    "biorisk": ("safety", "biology risk evaluations"),
    "cloningscenarios": ("safety", "LAB-Bench subset: molecular cloning planning"),
    "figqa": ("capability", "LAB-Bench subset: figure interpretation"),
    "seqqa": ("capability", "LAB-Bench subset: DNA/protein sequence questions"),
    "mlebench": ("capability", "ML engineering Kaggle tasks; AI R&D proxy"),
    "paperbench": ("capability", "paper replication; AI R&D proxy"),
    "swelancer": ("capability", "freelance software tasks"),
    "frontiermath": ("capability", "research-level maths"),
    "taubench": ("capability", "tool-use agent benchmark"),
    "xstest": ("safety", "over-refusal on benign prompts"),
    "sorrybench": ("safety", "refusal on unsafe requests"),
    "jailbreakbench": ("safety", "jailbreak robustness"),
    "wildjailbreak": ("safety", "in-the-wild jailbreak prompts"),
    "truthfulqa": ("safety", "imitative falsehoods"),
    "toxigen": ("safety", "implicit toxicity"),
    "graysw": ("org", "red-teaming vendor"),
    "grayswanarena": ("safety", "crowd-sourced jailbreak arena"),
    "agentdojo": ("safety", "prompt-injection robustness for agents"),
    "biolpbench": ("safety", "lab protocol error correction (bio uplift)"),
    "asimov": ("safety", "robotics constitution eval"),
    "cybergym": ("safety", "real-world vulnerability reproduction tasks"),
    "bountybench": ("safety", "bug-bounty exploit tasks"),
    "cvebench": ("safety", "real CVE exploitation"),
    "intercodectf": ("safety", "entry-level CTF"),
    "nyuctf": ("safety", "CTF from NYU CSAW"),
    "picoctf": ("safety", "high-school CTF"),
    "hackthebox": ("safety", "penetration-testing boxes"),
    "secbench": ("safety", "cybersecurity knowledge"),
    "chembench": ("safety", "chemistry knowledge, chem uplift proxy"),
    "modelspec": ("policy", "OpenAI behaviour specification, not an eval"),
    "persuasion": ("safety", "persuasiveness vs humans"),
    "makemepay": ("safety", "manipulation: conning another model out of money"),
    "makemesay": ("safety", "manipulation: steering another model to say a codeword"),
    "ailuminate": ("safety", "MLCommons harmful-response benchmark"),
    "airbench": ("safety", "regulation-derived risk taxonomy prompts"),
    "safetybench": ("safety", "multiple-choice safety knowledge"),
    "realtoxicityprompts": ("safety", "toxic continuation"),
    "wildchat": ("safety", "real user prompts incl. toxic"),
    "donotanswer": ("safety", "refusal on should-not-answer prompts"),
    "sycophancyeval": ("safety", "sycophancy suite"),
    "agentbench": ("capability", "agent tasks"),
    "cloudrunelicitation": ("safety", "cloud infra autonomy task"),
    "exploitbench": ("safety", "CVE exploit development in browser engines (Anthropic cyber)"),
    "exploitgym": ("safety", "real-vulnerability exploitation gym (cyber uplift)"),
    "cyscenariobench": ("safety", "multi-stage attack scenario planning (Irregular)"),
    "ossfuzz": ("safety", "vulnerability discovery in fuzzed open-source targets"),
    "frontiercyber": ("safety", "Irregular's hard offensive-cyber challenge set"),
    "hackerbench": ("safety", "refusal on harmful cyber requests (xAI)"),
    "thelastonestlo": ("safety", "UK AISI 32-step full network takeover range"),
    "agentredteamingart": ("safety", "Gray Swan/UK AISI prompt-injection red-team arena"),
    "indirectpromptinjectionipi": ("safety", "prompt-injection robustness for agents"),
    "binaryexploitationbenchmark": ("safety", "binary exploitation (formerly OSS-Fuzz)"),
    "mbct": ("safety", "Molecular Biology Capabilities Test, bio-uplift proxy"),
    "hpct": ("safety", "Human Pathogen Capabilities Test, bio-uplift proxy"),
    "wcb": ("safety", "World Class Bio: rare expert bio knowledge"),
    "biotier": ("safety", "biosecurity refusal evaluation"),
    "abcbench": ("safety", "bio design/screening-evasion tasks (Meta)"),
    "reprobait": ("safety", "reproduce biological AI models from papers (SecureBio)"),
    "troubleshootingbench": ("safety", "open-ended wet-lab troubleshooting (OpenAI bio)"),
    "bixbench": ("capability", "bioinformatics analysis tasks"),
    "controlarena": ("safety", "UK AISI control setting: covert side tasks under monitoring"),
    "shushcast": ("safety", "covert side task while doing HCAST tasks (METR)"),
    "appsbackdoors": ("safety", "insert backdoors in APPS solutions covertly"),
    "minimallinuxbench": ("safety", "monitor-evasion / stealth in Linux admin tasks"),
    "epochcapabilitiesindexeci": ("capability", "aggregate capability index across benchmarks"),
    "cobench": ("capability", "AI R&D acceleration tasks (Anthropic)"),
    "posttrainbench": ("capability", "automating LLM post-training; AI R&D proxy"),
    "gdpval": ("capability", "economically valuable professional tasks"),
    "healthbench": ("capability", "medical conversation quality; harm-adjacent"),
    "deepsearchqa": ("capability", "multi-step web research"),
    "deepswe": ("capability", "long-horizon software engineering"),
    "mmmu": ("capability", "multimodal college-level QA"),
    "programbench": ("capability", "long-context programming"),
    "charxiv": ("capability", "chart understanding"),
    "matharena": ("capability", "live competition maths"),
    "officeqa": ("capability", "grounded reasoning over office documents"),
    "biomysterybench": ("capability", "analytical life-science puzzles"),
    "cursorbench": ("capability", "IDE coding tasks (Cursor)"),
    "frontierswe": ("capability", "frontier software engineering tasks"),
    "frontiercode": ("capability", "frontier coding tasks"),
    "screenspot": ("capability", "GUI grounding"),
    "mmmlu": ("capability", "multilingual MMLU"),
    "automationbench": ("capability", "workflow automation tasks"),
    "dronebench": ("capability", "drone control (Andon Labs)"),
    "mrcr": ("capability", "long-context multi-round coreference"),
    "spatialbench": ("capability", "spatial transcriptomics analysis"),
    "gsm8k": ("capability", "grade-school maths"),
    "bfcl": ("capability", "function-calling leaderboard"),
    "livecodebench": ("capability", "competitive programming"),
    "frontierbench": ("capability", "frontier reasoning tasks"),
    "apexswe": ("capability", "software engineering tasks"),
    "eebench": ("capability", "electrical engineering / chip design"),
    "gmmlu": ("capability", "global multilingual MMLU"),
    "milu": ("capability", "Indic language understanding"),
    "relbench": ("capability", "relational data prediction"),
    "riemannbench": ("capability", "research maths"),
    "arxivmath": ("capability", "maths from arXiv papers"),
    "benchcad": ("capability", "programmatic CAD reasoning"),
    "toolathlon": ("capability", "tool-use marathon"),
    "aabriefcase": ("capability", "professional briefcase tasks"),
    "legalagentbenchmark": ("capability", "legal agent tasks"),
    "proteingym": ("capability", "protein fitness prediction"),
    "mcpatlas": ("capability", "MCP tool-use tasks"),
    "graphwalks": ("capability", "long-context graph reasoning"),
    "chartography": ("capability", "chart reading"),
    "critpt": ("capability", "physics research problems"),
    "draco": ("capability", "agentic search"),
    "imo": ("capability", "olympiad maths"),
}

# Hand-curated shortlist: 10 famous safety evals covering the five domains.
SHORTLIST: list[dict] = [
    {"key": "wmdp", "risk_domain": "cbrn",
     "measures": "Hazardous-knowledge proxy: 3,668 multiple-choice questions on biosecurity, cybersecurity and chemical security, written so that high scores indicate knowledge that could give uplift to weapons development; also used as an unlearning target."},
    {"key": "vct", "risk_domain": "cbrn",
     "measures": "Virology Capabilities Test: multimodal troubleshooting questions on wet-lab virology protocols, scored against virologists' expert baselines, built by SecureBio to measure practical bio-uplift."},
    {"key": "cybench", "risk_domain": "cyber",
     "measures": "Professional capture-the-flag challenges (from HackTheBox, Sekai, Glacier, HKCert) with first-solve-time difficulty ratings, testing whether an agent can find and exploit vulnerabilities end to end."},
    {"key": "cybergym", "risk_domain": "cyber",
     "measures": "Real-world vulnerability reproduction: given a codebase and a vulnerability description, the agent must write a proof-of-concept input that triggers the bug (from OSS-Fuzz crash data); a cyber-uplift proxy run by most labs."},
    {"key": "cyberrange", "risk_domain": "cyber",
     "measures": "Multi-stage network attack simulations (reconnaissance, lateral movement, exfiltration) in a realistic emulated enterprise, used to test whether models can autonomously conduct full cyber operations."},
    {"key": "shadearena", "risk_domain": "loss_of_control",
     "measures": "Agentic environments where a model must complete a main task while covertly pursuing a harmful side task without being flagged by an LLM monitor; measures sabotage and evasion capability."},
    {"key": "agenticmisalignment", "risk_domain": "loss_of_control",
     "measures": "Scenarios in which an agent with corporate access faces replacement or goal conflict and can choose blackmail, leaking or other insider threats; measures willingness to take harmful actions to preserve itself."},
    {"key": "mask", "risk_domain": "harmful_manipulation",
     "measures": "Honesty under pressure: compares a model's elicited belief with what it states when incentivised to lie, separating honesty from accuracy; the standard deception/lying benchmark cited by many labs."},
    {"key": "strongreject", "risk_domain": "societal_harm",
     "measures": "Jailbreak robustness: forbidden prompts paired with jailbreak techniques, graded by a rubric on specificity and convincingness of harmful compliance rather than refusal-string matching."},
    {"key": "bbq", "risk_domain": "societal_harm",
     "measures": "Bias Benchmark for QA: ambiguous and disambiguated questions about protected groups; reports accuracy and bias score to detect stereotyped answers."},
]

COST_VALIDITY_RE = re.compile(
    r"(\b\d[\d,]*\s*(?:tasks?|questions?|problems?|items|scenarios|challenges|prompts|samples|"
    r"trajectories|environments|attempts|runs|rollouts|transcripts)\b|"
    r"\b\d+(?:\.\d+)?\s*(?:hours?|hrs|minutes|days|weeks|person-hours|expert-hours)\b|"
    r"(?:human|expert)s?[- ]baselines?|inter-?rater|agreement|Cohen|kappa|correlat|validity|"
    r"contaminat|saturat|noise|variance|confidence interval|error bars?|standard error|bootstrap|"
    r"first[- ]solve|cost|\$\d|judge|grader|rubric|human[- ]rated|annotat|calibrat|"
    r"\bn ?= ?\d|per (?:task|question|challenge)|(?:pass|solve|success|action|blackmail|stealth|honesty|refusal) rates?)",
    re.I,
)
INFO_WORDS_RE = re.compile(
    r"\b(tasks?|questions?|problems?|items|scenarios|challenges|prompts|baselines?|experts?|hours?|"
    r"agreement|measures?|designed|assess|evaluat|consists?|comprises?|tests?|multiple[- ]choice|"
    r"dataset|benchmark|score[sd]?|accuracy|pass rate|solve rate|success rate)\b",
    re.I,
)


ABBREV_RE = re.compile(r"\b(e\.g|i\.e|et al|vs|cf|Fig|No|approx|Dr|Mr|Ms|Prof|Inc|Ltd|St)\.")


def sentences(text: str) -> list[str]:
    protected = ABBREV_RE.sub(lambda m: m.group(1) + "\u2024", text)  # one-dot leader as placeholder
    return [s.replace("\u2024", ".").strip() for s in SENT_SPLIT_RE.split(protected) if s.strip()]


def sentence_score(s: str, name_re: re.Pattern) -> float:
    n = len(s)
    score = 0.0
    if 80 <= n <= 350:
        score += 1.0
    if n < 40 or n > 550:
        score -= 3.0
    nums = re.findall(r"\d+(?:\.\d+)?%?", s)
    if nums:
        score += 2.0
    if len(nums) > 8:
        score -= 2.0  # table row
    score += min(len(INFO_WORDS_RE.findall(s)), 5) * 0.6
    if re.match(r"^(Figure|Table|Section|Appendix)\b", s):
        score -= 2.0
    if re.search(r"\.{3}|\|", s) or s.count("●") > 1:
        score -= 1.0
    words = WORD_RE.findall(s)
    if len(words) < 8:
        score -= 2.0
    toks = s.split()
    numeric = sum(1 for t in toks if re.fullmatch(r"[\d.,%()~∼–-]+", t))
    if toks and numeric / len(toks) > 0.2:
        score -= 3.0  # table row pasted into running text
    if re.search(r"arXiv|preprint|https?://|doi\.org|MODEL CARD|Page \d+/\d+", s):
        score -= 3.0  # bibliography entry or page furniture
    if re.search(r".{15,}\b\d+\.\d+(?:\.\d+)* [A-Z][A-Za-z-]{2,}", s) or s.startswith("Metric "):
        score -= 2.5  # a section heading or table header glued mid-sentence (PDF extraction)
    if re.search(r"\((?:high|low|medium|max)\)", s):
        score -= 2.0  # effort-level column headers from a results table
    if name_re.search(s[:120]):
        score += 0.5  # name early -> sentence is about it
    return score


def content_words(s: str) -> frozenset:
    return frozenset(w.lower() for w in WORD_RE.findall(s) if len(w) >= 4 and not w[0].isdigit())


def is_near_duplicate(words: frozenset, seen: list[frozenset], thr: float = 0.7) -> bool:
    for other in seen:
        inter = len(words & other)
        if inter and inter / len(words | other) >= thr:
            return True
    return False


def collect_snippets(docs, key: str, max_n: int):
    pats = SEEDS.get(next((n for n in SEEDS if norm_key(n) == key), ""), [])
    name_re = re.compile("|".join(pats)) if pats else re.compile(re.escape(key), re.I)
    cands = []
    seen_words: list[frozenset] = []
    for d in docs:
        for pos, s in enumerate(sentences(d["text"])):
            if not name_re.search(s):
                continue
            words = content_words(s)
            if not words or is_near_duplicate(words, seen_words):
                continue  # system cards recycle paragraphs; cursor/xai publish the same card
            seen_words.append(words)
            cands.append(
                {
                    "sentence": s,
                    "slug": d["slug"],
                    "publisher": d["publisher"],
                    "score": round(sentence_score(s, name_re), 2),
                    "pos": pos,
                    "cost_validity": bool(COST_VALIDITY_RE.search(s)),
                }
            )
    cands.sort(key=lambda c: (-c["score"], c["slug"], c["pos"]))
    # round-robin across publishers, then docs, for diversity; only sentences with a
    # non-negative score enter the pool so a publisher's "best" is never a table row
    by_pub: dict[str, list] = defaultdict(list)
    for c in cands:
        if c["score"] >= 0:
            by_pub[c["publisher"]].append(c)
    pub_order = sorted(by_pub, key=lambda p: (-by_pub[p][0]["score"], p))
    picked, used_docs = [], Counter()
    while len(picked) < max_n and any(by_pub.values()):
        for p in pub_order:
            lst = by_pub[p]
            while lst and used_docs[lst[0]["slug"]] >= 3:
                lst.pop(0)
            if lst:
                c = lst.pop(0)
                used_docs[c["slug"]] += 1
                picked.append(c)
                if len(picked) >= max_n:
                    break
    return picked, cands


# --------------------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------------------
def write_outputs(docs, rows, dropped, out_dir: Path, top_n: int):
    out_dir.mkdir(parents=True, exist_ok=True)
    N = len(docs)
    pubs = Counter(d["publisher"] for d in docs)
    dom_counts = {dom: sum(dom in d["domains"] for d in docs) for dom in DOMAINS}
    by_key = {r["key"]: r for r in rows}

    (out_dir / "system_card_evals.json").write_text(
        json.dumps(
            {
                "n_docs": N,
                "publishers": dict(sorted(pubs.items())),
                "domain_doc_counts": dom_counts,
                "dropped_by_filter": dict(sorted(dropped.items())),
                "rank_score": "df * (1 + ln(n_publishers))",
                "tfidf": "sum over docs of (mentions/doc_words) * ln(N/df), x1e4",
                "domain_lift": "smoothed share of the eval's informative docs (1-3 domain tags, weight 1/k) in the domain / base rate; 'unresolved' top_domain = only mentioned in uninformative docs",
                "candidates": rows,
            },
            indent=1,
        )
        + "\n"
    )

    # ---- snippets for the shortlist ----
    snippets = {}
    shortlist_detail = []
    for item in SHORTLIST:
        r = by_key.get(item["key"])
        if r is None:
            continue
        picked, all_cands = collect_snippets(docs, item["key"], 15)
        snippets[r["name"]] = {
            "risk_domain": item["risk_domain"],
            "df": r["df"],
            "n_publishers": r["n_publishers"],
            "publishers": r["publishers"],
            "snippets": [
                {k: c[k] for k in ("sentence", "slug", "publisher", "score", "cost_validity")}
                for c in picked
            ],
        }
        cost = [c for c in all_cands if c["cost_validity"] and c["score"] >= 1.0]
        cost.sort(key=lambda c: (-c["score"], c["slug"], c["pos"]))
        shortlist_detail.append({**item, "row": r, "top3": picked[:3], "cost": cost[:6]})
    (out_dir / "system_card_snippets.json").write_text(json.dumps(snippets, indent=1) + "\n")

    # ---- markdown ----
    md = []
    md.append("# Evaluations named in frontier system cards and third-party eval reports\n")
    md.append(f"Corpus: {N} documents with safety_evals=1 from {len(pubs)} publishers "
              f"({', '.join(f'{p} {n}' for p, n in pubs.most_common())}).\n")
    md.append("Domain document counts: " + ", ".join(f"{k} {v}" for k, v in dom_counts.items()) + ".\n")
    md.append(f"Candidates kept: {len(rows)}. Dropped by filter: "
              + ", ".join(f"{k} {v}" for k, v in sorted(dropped.items())) + ".\n")
    md.append("Rank score = DF x (1 + ln n_publishers). Top domain = domain with highest smoothed "
              "lift, computed only over docs tagged with 1-3 risk domains (the comprehensive system "
              "cards are tagged with all five and carry no signal); 'unresolved' = only mentioned in "
              "such uninformative docs. For capability benchmarks the domain is incidental. Label: safety = measures a "
              "risk or alignment property; capability = general capability benchmark that is not "
              "itself a risk measure; org = evaluator, not an eval.\n")
    md.append(f"\n## Top {top_n} candidates\n")
    md.append("| # | name | DF | pubs | mentions | top domain (lift) | label | why |")
    md.append("|---|---|---|---|---|---|---|---|")
    for i, r in enumerate(rows[:top_n], 1):
        lab, why = LABELS.get(r["key"], ("unlabelled", ""))
        md.append(
            f"| {i} | {r['name']} | {r['df']} | {r['n_publishers']} | {r['total_mentions']} | "
            f"{r['top_domain']} ({r['domain_lift'].get(r['top_domain'], '-')}) | {lab} | {why} |"
        )

    md.append("\n## Shortlist: 10 safety evaluations spanning the five risk domains\n")
    md.append("| name | domain | DF | pubs | publishers |")
    md.append("|---|---|---|---|---|")
    for it in shortlist_detail:
        r = it["row"]
        md.append(f"| {r['name']} | {it['risk_domain']} | {r['df']} | {r['n_publishers']} | "
                  f"{', '.join(r['publishers'])} |")
    for it in shortlist_detail:
        r = it["row"]
        md.append(f"\n### {r['name']} ({it['risk_domain']})\n")
        md.append(f"What it measures: {it['measures']}\n")
        md.append(f"Cited by ({r['n_publishers']} publishers, {r['df']} docs): {', '.join(r['publishers'])}.\n")
        md.append("Domain DF: " + ", ".join(f"{k} {v}" for k, v in r["domain_df"].items()) + ".\n")
        md.append("Most informative sentences:\n")
        for c in it["top3"]:
            md.append(f"- \"{c['sentence']}\" ({c['slug']})")
        if it["cost"]:
            md.append("\nCost / validity information in the corpus:\n")
            for c in it["cost"]:
                md.append(f"- \"{c['sentence']}\" ({c['slug']})")
        else:
            md.append("\nCost / validity information in the corpus: none found by the regex filter.\n")
    (out_dir / "system_card_evals.md").write_text("\n".join(md) + "\n")
    return shortlist_detail


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", type=Path, default=DEFAULT_DB)
    ap.add_argument("--out-dir", type=Path, default=Path(__file__).resolve().parent)
    ap.add_argument("--top", type=int, default=60)
    ap.add_argument("--debug-top", type=int, default=0, help="print the top-K table to stdout")
    args = ap.parse_args()

    docs = load_docs(args.db)
    per_doc, surface, is_seed, word_counter = extract_candidates(docs)
    rows, dropped = compute_table(docs, per_doc, surface, is_seed, word_counter)
    detail = write_outputs(docs, rows, dropped, args.out_dir, args.top)

    print(f"docs={len(docs)} candidates={len(rows)} dropped={dict(dropped)}")
    if args.debug_top:
        for i, r in enumerate(rows[: args.debug_top], 1):
            lab = LABELS.get(r["key"], ("?",))[0]
            print(f"{i:3d} {r['name']:32s} df={r['df']:3d} pubs={r['n_publishers']:2d} "
                  f"m={r['total_mentions']:5d} {r['top_domain']:20s} {lab:10s} "
                  f"{list(r['forms'].items())[:3]}")
    print(json.dumps([
        {"name": it["row"]["name"], "risk_domain": it["risk_domain"], "df": it["row"]["df"],
         "n_publishers": it["row"]["n_publishers"]} for it in detail
    ]))


if __name__ == "__main__":
    main()
