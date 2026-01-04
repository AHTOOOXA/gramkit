import type { MockUser } from '@core/platform-mock';

/**
 * Mock users for platform testing in debug mode
 */
export const MOCK_USERS: MockUser[] = [
  {
    user_id: 7934526008,
    username: 'ReallyCoolSupport',
    display_name: 'Katya',
    avatar_url:
      'https://t.me/i/userpic/320/hUiiHPraMdflrwLN5nuAhcZQN4QsyVx8NiieccatyeBv1I8u4eAOah5sgP75FZX3.svg',
    user_type: 'REGISTERED',
  },
  {
    user_id: 987654321,
    username: 'dev',
    display_name: 'Dev User',
    avatar_url: undefined,
    user_type: 'REGISTERED',
  },
  {
    user_id: 123456789,
    username: 'anton_whatever',
    display_name: 'Anton',
    avatar_url: 'https://t.me/i/userpic/320/UodwQMzZvdFeOA_xaUzsE4JveHPsTct_gfSi78xkw_0.svg',
    user_type: 'REGISTERED',
  },
];
