export interface MockUser {
  user_id: number;
  username: string;
  first_name: string;
  last_name?: string;
  photo_url?: string;
  user_type: 'REGISTERED';
  app_username: string;
}

/**
 * Mock users for platform testing in debug mode
 */
export const MOCK_USERS: MockUser[] = [
  {
    user_id: 7934526008,
    username: 'ReallyCoolSupport',
    first_name: 'Катя',
    last_name: '',
    photo_url:
      'https://t.me/i/userpic/320/hUiiHPraMdflrwLN5nuAhcZQN4QsyVx8NiieccatyeBv1I8u4eAOah5sgP75FZX3.svg',
    user_type: 'REGISTERED',
    app_username: 'ReallyCoolSupport',
  },
  {
    user_id: 987654321,
    username: 'dev',
    first_name: 'Dev',
    last_name: 'User',
    photo_url: undefined,
    user_type: 'REGISTERED',
    app_username: 'dev',
  },
  {
    user_id: 123456789,
    username: 'anton_whatever',
    first_name: 'Anton',
    last_name: '',
    photo_url:
      'https://t.me/i/userpic/320/UodwQMzZvdFeOA_xaUzsE4JveHPsTct_gfSi78xkw_0.svg',
    user_type: 'REGISTERED',
    app_username: 'anton_whatever',
  },
];
