import {defineConfig} from '@playwright/test';
import base from './playwright.config';

export default defineConfig({
  ...base,
  testMatch:['mobile.spec.ts','interactions.spec.ts','summary.spec.ts'],
  grepInvert:/baseline/,
  use:{...base.use,browserName:'webkit',viewport:{width:390,height:844},isMobile:true,hasTouch:true,deviceScaleFactor:3},
});
