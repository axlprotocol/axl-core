// AXL Protocol — Product Use Cases & Funding
// For axlprotocol.org/products and axlprotocol.org/invest

const USE_CASES = {

  // ═══════════════════════════════════════════════════════════
  // CASE 1: CONTEXT COMPRESSION (the viral entry point)
  // ═══════════════════════════════════════════════════════════
  case_1: {
    name: "AXL Compress",
    url: "compress.axlprotocol.org",
    tagline: "Fit 10x more into your LLM context window",
    problem: `
      GPT-5 has a 200K context window. Your research paper is 45 pages.
      You paste it in. Half gets truncated. The LLM misses critical data.
      You're paying for 200K tokens and getting mediocre results because
      the input is bloated with grammatical scaffolding.
    `,
    solution: `
      Paste your document into AXL Compress. Get a compressed version that
      preserves all semantic content in 1/10th the tokens. Paste the
      compressed version into ANY LLM. The Rosetta header teaches the LLM
      to decode it on first read. Your 45-page paper now fits in 4.5 pages
      of context. The LLM sees everything. You pay for 10x fewer tokens.
    `,
    example: {
      before: `
        "Magnesium acts as a cofactor for over 300 enzyme systems that regulate
        diverse biochemical reactions in the body, including protein synthesis,
        muscle and nerve function, blood glucose control, and blood pressure
        regulation. Magnesium is required for energy production, oxidative
        phosphorylation, and glycolysis. It contributes to the structural
        development of bone and is required for the synthesis of DNA, RNA,
        and the antioxidant glutathione."
        
        → 67 tokens
      `,
      after: `
        π:BIO-01|OBS.95|#Mg_cofactor|^300_enzyme_systems|
        $protein_synth+$nerve_func+$glucose_ctrl+$BP_reg+
        $energy_prod+$bone_struct+$DNA_RNA_synth+$glutathione|NOW
        
        → 28 tokens (2.4x compression on this excerpt, 10x+ on full documents)
      `
    },
    monetization: "Free tier (10/day) → Pro $29/mo (unlimited + API)",
    viral_mechanism: "Every compressed output includes @axlprotocol.org/rosetta. Every LLM that reads it learns AXL."
  },

  // ═══════════════════════════════════════════════════════════
  // CASE 2: MULTI-EXPERT DELIBERATION (the core product)
  // ═══════════════════════════════════════════════════════════
  case_2: {
    name: "AXL Swarm",
    url: "swarm.axlprotocol.org",
    tagline: "12 experts debate your question. You get the consensus.",
    problem: `
      You ask ChatGPT a complex medical/legal/financial question.
      You get ONE perspective from ONE model. No debate. No disagreement.
      No synthesis of multiple viewpoints. No belief changes. Just one
      confident answer that might be wrong.
    `,
    solution: `
      Write a seed document describing your question and the experts you want.
      AXL Swarm spawns 10-20 agents with different personas and expertise.
      They debate for 12 rounds. They disagree. They change their minds.
      They converge on a consensus — or they don't, and you see why.
      The output is a structured prediction signal, not a single opinion.
    `,
    examples: [
      "Medical: 12 doctors debate whether a mass is cancer or endometriosis → consensus: MRI first",
      "Military: 10 intelligence analysts assess invasion probability → consensus: 67% likely, 72h window",
      "Legal: 10 experts debate a $47M contract dispute → consensus: mediation, not litigation",
      "Personal: 10 advisors debate whether to quit your job → structured decision framework",
      "Finance: 12 traders debate BTC direction → weighted prediction with confidence intervals",
    ],
    monetization: "Free (3 seeds/month) → Pro $99/mo (unlimited + API + custom seeds)",
    proven: "10.41x compression. 95% AXL adoption. 37x engagement. 8 domains validated."
  },

  // ═══════════════════════════════════════════════════════════
  // CASE 3: AGENT INTEROPERABILITY (the platform play)
  // ═══════════════════════════════════════════════════════════
  case_3: {
    name: "AXL Bridge",
    url: "bridge.axlprotocol.org",
    tagline: "Make any AI agent talk to any other AI agent",
    problem: `
      Your company uses LangChain for customer support agents, CrewAI for
      research agents, and AutoGen for code review agents. They can't
      share information. The customer support agent discovers a bug pattern
      but can't tell the code review agent. The research agent finds a
      competitive threat but can't alert the customer support agent.
      Your AI agents are siloed.
    `,
    solution: `
      AXL Bridge translates between frameworks. Each agent gets an AXL
      endpoint. They communicate through AXL packets — framework-agnostic,
      compressed, typed. The LangChain agent sends an OBS packet about the
      bug pattern. The AutoGen agent receives it, understands it (same
      Rosetta), and acts on it. Zero integration code. One protocol.
    `,
    monetization: "Enterprise. Custom pricing per agent connection.",
    status: "Roadmap — requires Proof 2 (cross-framework interop) completion."
  },

  // ═══════════════════════════════════════════════════════════
  // CASE 4: INTELLIGENCE DASHBOARD (the Sophon product)
  // ═══════════════════════════════════════════════════════════
  case_4: {
    name: "Sophon",
    url: "sophon.axlprotocol.org",
    tagline: "Watch your agents think. See consensus form in real-time.",
    problem: `
      You run a multi-agent system. 50 agents processing data.
      You have no visibility. You don't know what they're concluding,
      who disagrees, when beliefs change, or whether consensus is forming.
      It's a black box.
    `,
    solution: `
      Sophon reads AXL packets from your agent swarm and presents:
      - Belief state table: what each agent thinks right now
      - Consensus meter: is the swarm converging or diverging?
      - Influence chains: who changed whose mind?
      - Prediction signal: what the collective intelligence says
      - Timeline replay: scrub through the deliberation frame by frame
      
      Web dashboard (HTML, any browser) + 3D visualization (Blender, GPU)
    `,
    monetization: "Included with Swarm tier. Standalone: $49/mo for external agent monitoring.",
    status: "Web monitor built. 3D Blender renderer operational."
  },

  // ═══════════════════════════════════════════════════════════
  // CASE 5: PROMPT COMPRESSION API (the developer tool)
  // ═══════════════════════════════════════════════════════════
  case_5: {
    name: "AXL API",
    url: "api.axlprotocol.org",
    tagline: "Compress any prompt. Save 10x on API costs.",
    problem: `
      You're building an AI application. Your system prompts are 8,000 tokens.
      Your RAG context is 15,000 tokens. Your conversation history is 10,000
      tokens. Every API call costs $0.10. At 100K calls/day, you're spending
      $10,000/day on tokens — 80% of which are grammatical scaffolding.
    `,
    solution: `
      AXL API sits between your application and your LLM provider.
      It compresses system prompts, RAG context, and conversation history
      into AXL format before sending to the LLM. The LLM reads the Rosetta
      header (cached after first call), processes the compressed input,
      and responds. Your 33,000-token call becomes 8,000 tokens.
      Your $10,000/day becomes $2,500/day.
    `,
    monetization: "Usage-based: $0.50 per 1M tokens compressed. Free tier: 100K tokens/day.",
    status: "Requires compression benchmarks beyond deliberation. Research phase."
  }
};


// ═══════════════════════════════════════════════════════════
// FUNDING STRATEGY
// ═══════════════════════════════════════════════════════════

const FUNDING = {
  round: "Pre-Seed / Seed",
  target: "$1.5M - $3M CAD",
  use_of_funds: {
    "Protocol Engineering (40%)": "2 engineers — axl-core, Rosetta v3.0, cross-framework bridge",
    "Infrastructure (20%)": "Cloud compute, API hosting, monitoring",
    "Product (25%)": "compress.axlprotocol.org, swarm.axlprotocol.org, API",
    "Operations (15%)": "Legal, IP protection, conferences, team"
  },
  
  traction: {
    "Protocol validated": "10.41x compression, 95% adoption, 6 LLM architectures",
    "Open source": "4 GitHub repos, pip-installable package",
    "Cross-domain": "8 domains tested (finance, medical, military, science, philosophy, geopolitics, legal, personal)",
    "Academic foundation": "2 papers (technical whitepaper v2.3 + social protocol thesis)",
    "Infrastructure": "3 servers operational, Blender GPU pipeline, monitoring stack",
    "Community": "Public battleground results, reproducible experiments"
  },

  // CANADIAN VCs (Vancouver + Toronto focus)
  canadian_targets: [
    {
      name: "Radical Ventures",
      location: "Toronto",
      focus: "AI-first companies",
      why: "Backed Geoffrey Hinton. Deep AI thesis. AXL is infrastructure for the agent economy.",
      url: "https://radical.vc",
      stage: "Seed to Series A"
    },
    {
      name: "Inovia Capital",
      location: "Montreal / Waterloo",
      focus: "Enterprise software, AI infrastructure",
      why: "Portfolio includes AI companies. AXL fits their infrastructure thesis.",
      url: "https://inovia.vc",
      stage: "Seed to Series B"
    },
    {
      name: "BDC Capital (BDC Ventures)",
      location: "Montreal (national)",
      focus: "Canadian tech companies",
      why: "Government-backed but acts like a VC. Supports Canadian AI ecosystem.",
      url: "https://www.bdc.ca/en/bdc-capital",
      stage: "Seed to Growth"
    },
    {
      name: "Panache Ventures",
      location: "Calgary / Vancouver",
      focus: "Pre-seed and seed stage",
      why: "Western Canada focus. Active in Vancouver ecosystem. Quick decisions.",
      url: "https://www.panacheventures.com",
      stage: "Pre-seed"
    },
    {
      name: "N49P (Relay Ventures successor)",
      location: "Toronto",
      focus: "Connected intelligence, platforms",
      why: "Agent interoperability IS connected intelligence.",
      url: "https://www.n49p.com",
      stage: "Seed"
    },
    {
      name: "Innovate BC / InBC Investment Corp",
      location: "Vancouver",
      focus: "BC-based tech companies",
      why: "Government investment arm. Supports BC tech ecosystem. Web Summit Vancouver partner.",
      url: "https://www.innovatebc.ca",
      stage: "Various"
    },
    {
      name: "Creative Destruction Lab (CDL)",
      location: "Toronto / Vancouver",
      focus: "Science-based ventures, AI",
      why: "Not a VC but an accelerator with deep AI mentorship. Connects to Radical, Inovia.",
      url: "https://creativedestructionlab.com",
      stage: "Pre-seed"
    }
  ],

  // US VCs (AI infrastructure focus)
  us_targets: [
    {
      name: "a16z (crypto/AI intersection)",
      location: "San Francisco",
      focus: "Crypto + AI infrastructure",
      why: "AXL sits at the intersection — agent communication + x402 payments + soulbound identity. They wrote the thesis on crypto+AI convergence.",
      url: "https://a16zcrypto.com",
      stage: "Seed to Series A"
    },
    {
      name: "Sequoia Capital (Arc)",
      location: "Menlo Park",
      focus: "AI infrastructure",
      why: "Arc is their early-stage program. AXL is protocol infrastructure for the agent economy.",
      url: "https://www.sequoiacap.com/arc",
      stage: "Pre-seed / Seed"
    },
    {
      name: "Lux Capital",
      location: "New York",
      focus: "Deep tech, scientific breakthroughs",
      why: "They fund things that shouldn't work but do. AXL's self-bootstrapping acquisition is that kind of breakthrough.",
      url: "https://luxcapital.com",
      stage: "Seed to Series A"
    },
    {
      name: "Emergence Capital",
      location: "San Mateo",
      focus: "Enterprise AI, coaching/intelligence platforms",
      why: "Portfolio includes AI coaching and intelligence platforms. Sophon fits.",
      url: "https://www.emcap.com",
      stage: "Series A+"
    },
    {
      name: "AI Grant",
      location: "San Francisco",
      focus: "AI research grants",
      why: "Not a VC — a grant program. $250K-$500K. No equity. Funds AI research. AXL qualifies.",
      url: "https://aigrant.com",
      stage: "Grant"
    },
    {
      name: "Y Combinator",
      location: "San Francisco",
      focus: "Everything. The network is the value.",
      why: "The demo is pip install axl-swarm. YC loves one-command products. Apply for W26 or S26 batch.",
      url: "https://www.ycombinator.com/apply",
      stage: "Pre-seed"
    },
    {
      name: "Polychain Capital",
      location: "San Francisco",
      focus: "Crypto protocols",
      why: "AXL is a protocol with x402 micropayment economics. If you build the token economics layer, Polychain is the investor.",
      url: "https://polychain.capital",
      stage: "Seed to Series A"
    },
    {
      name: "Multicoin Capital",
      location: "Austin",
      focus: "Crypto infrastructure, DePIN",
      why: "Agent-to-agent communication with micropayments is DePIN for AI. Decentralized agent infrastructure.",
      url: "https://multicoin.capital",
      stage: "Seed to Series A"
    }
  ],

  pitch_deck_outline: [
    "1. The Problem — 3B agents by 2028, none can talk to each other",
    "2. The Cost — 22.5M tokens wasted on negotiation in a 100-agent network",
    "3. The Solution — AXL: 377 lines, one read, fluent. 10.41x compression.",
    "4. The Proof — 8 battlegrounds, 6 LLMs, 2 domains validated, open source",
    "5. The Product — compress.axlprotocol.org (free), swarm (pro), API (enterprise)",
    "6. The Market — $47B agent economy by 2028 (Gartner). Every agent needs a language.",
    "7. The Moat — Self-bootstrapping: every user teaches AXL to every LLM they touch",
    "8. The Team — [You + planned hires]",
    "9. The Ask — $2M seed. Protocol eng + product + infrastructure.",
    "10. The Vision — The lingua franca of the agent internet."
  ]
};

module.exports = { USE_CASES, FUNDING };
