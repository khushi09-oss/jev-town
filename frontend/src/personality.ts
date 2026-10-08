import type { Identity } from './contracts';

export const personalities: Record<Identity['trait'], {label: string; description: string}> = {
  social: {label: 'Social', description: 'Enjoys company and tends to seek it sooner.'},
  lazy: {label: 'Lazy', description: 'Likes a slower pace and tends to rest sooner.'},
  workaholic: {label: 'Workaholic', description: 'Often chooses work when there is energy to spare.'}
};
