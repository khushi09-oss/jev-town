import {it,expect} from 'vitest';
import {ambientPixels} from './ambience';
it('reconstructs the same ambient motion after a seek and respects reduced motion',()=>{
  const before=ambientPixels(14.75,false);
  expect(ambientPixels(15,false)).not.toEqual(before);
  expect(ambientPixels(14.75,false)).toEqual(before);
  expect(ambientPixels(14.75,true)).toEqual(ambientPixels(15,true));
  expect(before.every(p=>p.x>=916&&p.x<956&&p.y>=0&&p.y<640&&(p.y<350||p.y>400))).toBe(true);
});
