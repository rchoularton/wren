#!/usr/bin/env node
/**
 * create-research-assistant
 *
 * Interactive scaffolder for the Research Assistant Starter Kit. Run as an npm
 * initializer:
 *
 *     npm create research-assistant@latest my-research
 *
 * It copies the kit's template tree into the target directory, prompts for the
 * handful of fields that make the project yours, writes research-config.yml,
 * then renders templates + installs hooks by delegating to the shared Python
 * renderer (the same one `./setup.sh` uses).
 *
 * Zero runtime dependencies — Node built-ins only.
 */
import { createInterface } from 'node:readline/promises';
import { stdin, stdout } from 'node:process';
import { execFileSync } from 'node:child_process';
import { writeFileSync, existsSync, mkdirSync, readdirSync, cpSync, renameSync } from 'node:fs';
import { resolve, relative, basename, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const rl = createInterface({ input: stdin, output: stdout });

// Fall back to defaults when there's no interactive terminal (CI, piped input,
// `--yes`). Keeps scripted scaffolding deterministic instead of hanging on EOF.
const NONINTERACTIVE = !stdin.isTTY || process.argv.includes('--yes') || process.argv.includes('-y');

async function ask(question, fallback) {
  const suffix = fallback ? ` [${fallback}]` : '';
  if (NONINTERACTIVE) {
    console.log(`${question}${suffix}: ${fallback || ''}`);
    return fallback || '';
  }
  const answer = (await rl.question(`${question}${suffix}: `)).trim();
  return answer || fallback || '';
}

async function askChoice(question, choices, fallback) {
  const list = choices.join(' / ');
  let answer = await ask(`${question} (${list})`, fallback);
  answer = answer.toLowerCase();
  while (!choices.includes(answer)) {
    answer = (await ask(`  Please choose one of: ${list}`, fallback)).toLowerCase();
  }
  return answer;
}

async function askYesNo(question, fallback = false) {
  const def = fallback ? 'y' : 'n';
  const answer = (await ask(`${question} (y/n)`, def)).toLowerCase();
  return answer.startsWith('y');
}

// The installed package root is one level above this bin/ file.
const PACKAGE_ROOT = resolve(fileURLToPath(new URL('..', import.meta.url)));

function preflight() {
  // The renderer is Python; fail fast with a clear message if it's absent.
  try {
    execFileSync('python3', ['--version'], { stdio: 'ignore' });
  } catch {
    console.error('\n  This scaffolder needs Python 3.9+ on your PATH (the template renderer is Python).');
    console.error('  Install python3, then re-run.\n');
    process.exit(1);
  }
}

function yamlList(items) {
  if (!items.length) return '[]';
  return '\n' + items.map((i) => `    - "${i}"`).join('\n');
}

// Paths never copied into a fresh project: VCS/build noise and the *rendered*
// outputs (the .template / .example sources are copied instead).
// `.gitignore` ships as the non-dot `gitignore` (npm strips real dotfiles from
// tarballs) and is renamed after copy; `.npmignore` is maintainer-only.
const RENDERED = new Set([
  'research-config.yml', 'CLAUDE.md', 'CLAUDE_REFERENCE.md', '.mcp.json', '.env',
  '.gitignore', '.npmignore',
]);
function copyFilter(targetAbs) {
  return (src) => {
    if (src === targetAbs) return false; // never recurse into the target
    const rel = relative(PACKAGE_ROOT, src);
    if (!rel || rel.startsWith('..')) return true;
    const top = rel.split(sep)[0];
    if (top === 'node_modules' || top === '.git') return false;
    const base = basename(src);
    if (base === '.DS_Store' || base.endsWith('.tgz')) return false;
    if (RENDERED.has(rel)) return false;
    // Drop generated audit/run logs but keep the .gitkeep that holds the dir.
    if (rel.includes(`${sep}_logs${sep}`) && base !== '.gitkeep') return false;
    return true;
  };
}

async function resolveTargetDir() {
  // First non-flag positional is the target dir (so `--yes my-research` works).
  let arg = process.argv.slice(2).find((a) => !a.startsWith('-'));
  if (!arg) {
    arg = await ask('\n  New project directory', 'my-research');
  }
  const target = resolve(process.cwd(), arg);
  if (existsSync(target) && readdirSync(target).length > 0) {
    const proceed = await askYesNo(`  ${arg} already exists and is not empty. Continue and merge into it?`, false);
    if (!proceed) {
      console.log('  Aborted. Choose an empty directory name and re-run.\n');
      rl.close();
      process.exit(1);
    }
  }
  return target;
}

async function main() {
  console.log('\n  Research Assistant Starter Kit — setup\n  ' + '─'.repeat(40) + '\n');
  console.log('  Scaffolds a new project directory, then asks a few questions.');
  console.log('  Everything is editable later in research-config.yml — re-run');
  console.log('  ./setup.sh any time.\n');

  preflight();

  const root = await resolveTargetDir();

  // Copy the kit into the target before prompting, so setup.sh + the renderer
  // are present to run.
  mkdirSync(root, { recursive: true });
  console.log(`\n  Copying starter kit into ${relative(process.cwd(), root) || '.'} …`);
  cpSync(PACKAGE_ROOT, root, { recursive: true, filter: copyFilter(root) });

  // npm can't ship a real `.gitignore`, so the kit carries it as `gitignore`.
  // Restore the dotfile name in the new project.
  const shippedIgnore = resolve(root, 'gitignore');
  if (existsSync(shippedIgnore)) renameSync(shippedIgnore, resolve(root, '.gitignore'));

  const authorName = await ask('  Your name', 'Jane Researcher');
  const orcid = await ask('  ORCID (optional)', '');
  const email = await ask('  Email (optional, for digest drafts)', '');
  const projectName = await ask('  Project name', 'My Research Assistant');
  const namespace = (await ask('  Short namespace (lowercase, no spaces)', 'myresearch'))
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '');
  const discipline = await ask('  One-line description of your field', 'my research field');
  const journal = await ask('  Default target journal (optional)', 'Target Journal');

  const dbBackend = await askChoice(
    '  Research database backend',
    ['files', 'sqlite', 'duckdb', 'directus-local', 'managed'],
    'files'
  );

  const refProvider = await askChoice(
    '  Reference manager',
    ['bibtex', 'zotero', 'mendeley'],
    'bibtex'
  );
  let zoteroUserId = '';
  if (refProvider === 'zotero') {
    zoteroUserId = await ask('    Zotero user id (key goes in .env)', '');
  }
  if (refProvider === 'mendeley') {
    console.log('    Note: no turnkey Mendeley MCP exists yet. Export a .bib');
    console.log('    from Mendeley and the bibtex adapter will read it.');
  }

  const enableCorpus = await askYesNo('  Enable the corpus-memory add-on?', true);

  const config = `# Generated by create-research-assistant. Edit freely; re-run ./setup.sh to apply.
identity:
  author_name: "${authorName}"
  orcid: "${orcid}"
  email: "${email}"
  coauthors: []

project:
  name: "${projectName}"
  namespace: "${namespace}"
  discipline: "${discipline}"
  root: "${root}"

domain:
  key_terms: []

journals:
  default: "${journal}"
  targets: []

paths:
  protected_write_paths: []

database:
  backend: ${dbBackend}
  url: ""

references:
  provider: ${refProvider}
  bibtex_path: "references/library.bib"
  zotero:
    user_id: "${zoteroUserId}"
    api_key_env: "ZOTERO_API_KEY"

integrations:
  gmail:
    enabled: false

scheduler:
  platform: none
  jobs:
    nightly_memory:
      enabled: false
      at: "02:30"
    weekly_digest:
      enabled: false
      day: "Mon"
      at: "08:47"

notifications:
  enabled: true

tiers:
  research_memory: ${enableCorpus}
  qc_suite: false
  figure_suite: false
  librarian: false
`;

  const configPath = resolve(root, 'research-config.yml');
  if (existsSync(configPath)) {
    const overwrite = await askYesNo('\n  research-config.yml exists. Overwrite?', false);
    if (overwrite) writeFileSync(configPath, config);
    else console.log('  Keeping existing config. Running render only.\n');
  } else {
    writeFileSync(configPath, config);
  }
  rl.close();

  console.log('\n  Wrote research-config.yml. Running setup (render + hooks + verify)…\n');
  try {
    // setup.sh ensures PyYAML, renders templates, installs hooks, and verifies.
    execFileSync('bash', [resolve(root, 'setup.sh')], { stdio: 'inherit', cwd: root });
  } catch (e) {
    console.error('\n  Setup step failed. See the message above; fix and re-run ./setup.sh.');
    process.exit(1);
  }

  const cdHint = relative(process.cwd(), root) || '.';
  console.log(`\n  Done. Open the project in Claude Code:\n    cd ${cdHint}\n  then try:  /paper\n`);
}

main().catch((e) => {
  console.error(e);
  rl.close();
  process.exit(1);
});
