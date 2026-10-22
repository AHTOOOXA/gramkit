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
 * Mock users for platform testing in debug mode (fake data — replace freely)
 */
export const MOCK_USERS: MockUser[] = [
  {
    user_id: 123456789,
    username: 'alex_demo',
    first_name: 'Alex',
    last_name: 'Demo',
    photo_url: undefined,
    user_type: 'REGISTERED',
    app_username: 'alex_demo',
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
    user_id: 111222333,
    username: 'sam_demo',
    first_name: 'Sam',
    last_name: 'Demo',
    photo_url: undefined,
    user_type: 'REGISTERED',
    app_username: 'sam_demo',
  },
];
