#!/usr/bin/env node
// scripts/sync-extension-version.js
//
// Chrome zahteva statičen "version" niz neposredno v manifest.json —
// extension ne more brati /VERSION dinamično ob zagonu (za razliko od
// backenda, ki VERSION bere ob vsakem klicu, in UI-ja, ki ga vgradi ob
// buildu). Ta script je edini preostali ročni korak v sicer "eno mesto
// za verzijo" sistemu — poženi ga PRED pakiranjem extension za Chrome
// Web Store (ali pred vsakim `git commit` ki spreminja VERSION, da
// manifest.json ne zaostane).
//
// Uporaba:
//   node scripts/sync-extension-version.js

const fs = require('fs')
const path = require('path')

const ROOT = path.join(__dirname, '..')
const VERSION_PATH = path.join(ROOT, 'VERSION')
const MANIFEST_PATH = path.join(ROOT, 'loom-extension', 'manifest.json')

function main() {
  const version = fs.readFileSync(VERSION_PATH, 'utf-8').trim()

  const manifestRaw = fs.readFileSync(MANIFEST_PATH, 'utf-8')
  const manifest = JSON.parse(manifestRaw)

  if (manifest.version === version) {
    console.log(`manifest.json je že usklajen (${version}) — ni sprememb.`)
    return
  }

  const oldVersion = manifest.version
  manifest.version = version

  // Ohrani formatting (2-presledčni indent), skladno z ostalimi manifest.json
  // urejanji v tem repoju — brez tega bi diff pokazal spremembo celotne
  // datoteke namesto samo ene vrstice.
  fs.writeFileSync(MANIFEST_PATH, JSON.stringify(manifest, null, 2) + '\n', 'utf-8')

  console.log(`manifest.json posodobljen: ${oldVersion} → ${version}`)
}

main()
