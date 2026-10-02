// Local UI-only discovery. Emits an apply_patch document; never reads patient data/env.
const fs = require('fs'), path = require('path');
const read = p => fs.readFileSync(p,'utf8');
const list = p => fs.readdirSync(p,{withFileTypes:true}).flatMap(e => e.isDirectory() ? list(path.join(p,e.name)) : [path.join(p,e.name).replaceAll('\\','/')]);
const code = p => `\n## ${p}\n\n\`\`\`\n${read(p)}\n\`\`\`\n`;
const entries = list('frontend/app').filter(p=>p.endsWith('page.tsx'));
function dependencies(p, seen=new Set(), depth=0) {
  if (seen.has(p)) return ''; seen.add(p);
  let result = `${'  '.repeat(depth)}- ${p}\n`;
  for (const m of read(p).matchAll(/from\s+["']([^"']+)["']/g)) {
    const imp=m[1]; if (!imp.startsWith('.')&&!imp.startsWith('@/')) continue;
    const base=imp.startsWith('@/') ? 'frontend/'+imp.slice(2) : path.join(path.dirname(p),imp).replaceAll('\\','/');
    const target=[base,base+'.tsx',base+'.ts',base+'/index.ts'].find(x=>fs.existsSync(x)&&fs.statSync(x).isFile());
    if(target) result+=dependencies(target,seen,depth+1);
  } return result;
}
const tokens = `# Existing theme\nNext.js 16 / React 19, Tailwind 4, shadcn-style Button, Lucide, Recharts, NiiVue.\nBackground #0b121c; surface #111c29; surface-alt #142231; border #223141; text #e7eef6; muted #93a5b8; cyan #66dfd2; radius 12px. Inter/Segoe UI/Arial; body 14px/1.55; h1 31px/600, h2 17px/600, h3 15px/600. Buttons 40px minimum, 7px radius, 12px/650. Dark navy clinical-research workspace. CSS is authoritative for spacing/shadows/responsiveness. Tailwind 4 has no separate config.\n`;
const files={
 '.superdesign/init/components.md':'# Shared primitives\n'+code('frontend/components/ui/button.tsx')+code('frontend/components/common.tsx'),
 '.superdesign/init/layouts.md':'# Layouts\n'+code('frontend/app/layout.tsx')+code('frontend/app/(workspace)/layout.tsx')+code('frontend/components/shell.tsx'),
 '.superdesign/init/routes.md':'# Next.js file routes\n'+entries.map(p=>'- '+p+' (workspace routes use Shell; login is standalone)').join('\n'),
 '.superdesign/init/theme.md':tokens+code('frontend/app/globals.css'),
 '.superdesign/init/pages.md':'# Complete page dependencies\n'+entries.map(p=>'\n## '+p+'\n'+dependencies(p)).join('\n'),
 '.superdesign/init/extractable-components.md':'# Extractable components\n## WorkspaceSidebar\n- Source: frontend/components/shell.tsx\n- Category: layout\n- Description: persistent local research navigation/sidebar portion of Shell.\n- Props: activeItem string, default patients.\n- Hardcoded: NeuroPredict AI text, Lucide brain mark (no image logo exists), navigation labels/styles, local privacy and research disclaimers.\n## Button\n- Source: frontend/components/ui/button.tsx\n- Category: basic\n- Description: shared action variants; inline in draft.\n',
 '.superdesign/design-system.md':tokens+'\nExtend existing patient analysis; no new app/auth/viewer. Keep existing sidebar/topbar, original-MRI selection, baseline-conversion panel. New longitudinal anatomy feature: score estimates, measured region history and changes, QC, and current vs predicted-time viewer. Only synthetic placeholder cases; unavailable model outputs are null, not made-up scores/brains. Distinguish planned UI from functioning scientific pipeline. No external patient assets. Subtle transitions only; no crossfade presented as prediction.\n'
};
process.stdout.write('*** Begin Patch\n'+Object.entries(files).map(([p,v])=>'*** Add File: '+p+'\n'+v.replace(/\r/g,'').split('\n').map(l=>'+'+l).join('\n')+'\n').join('')+'*** End Patch\n');
