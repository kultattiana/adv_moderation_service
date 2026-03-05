import http from 'k6/http';
import { sleep, check } from 'k6';
import { randomIntBetween, randomItem, randomString } from 'https://jslib.k6.io/k6-utils/1.2.0/index.js';

export const options = {
  scenarios: {
    ramp: {
      executor: 'ramping-arrival-rate',
      startRate: 1,
      timeUnit: '1s',
      preAllocatedVUs: 50,
      maxVUs: 200,
      stages: [
        { target: 10, duration: '30s' },
        { target: 30, duration: '30s' }, 
        { target: 50, duration: '30s' },
        { target: 0, duration: '10s' },
      ],
    },
  }
};

const BASE = __ENV.BASE_URL || 'http://localhost:8000';


export function setup() {
  console.log('Регистрация тестовых пользователей...');
  
  const users = [];
  
  for (let i = 0; i < 3; i++) {
    const username = `testuser_${Date.now()}_${i}`;
    const userPayload = {
      username: username,
      email: `${username}@example.com`,
      password: 'testpassword123',
      is_verified: i % 2 == 0
    };
    
    const registerRes = http.post(`${BASE}/sellers/`, JSON.stringify(userPayload), {
      headers: { 'Content-Type': 'application/json' },
    });
    
    if (registerRes.status === 201) {
      const user = JSON.parse(registerRes.body);
      console.log(`Создан пользователь: ${user.username} с ID: ${user.seller_id}`);
      
      const loginPayload = {
        email: userPayload.email,
        password: userPayload.password
      };
      
      const loginRes = http.post(`${BASE}/login`, JSON.stringify(loginPayload), {
        headers: { 'Content-Type': 'application/json' },
      });
      
      if (loginRes.status === 200) {
        const cookies = loginRes.cookies['x-user-id'];
        users.push({
          seller_id: user.seller_id,
          email: userPayload.email,
          password: userPayload.password,
          cookies: { 'x-user-id': cookies }
        });
      }
    }
  }
  
  console.log('Создание тестовых объявлений...');
  
  const ads = [];
  for (const user of users) {
    const loginRes = http.post(`${BASE}/login`, 
      JSON.stringify({'email': user.email, 'password': user.password}), {
      headers: { 'Content-Type': 'application/json' },
    });

    const cookies = loginRes.cookies['x-user-id'];
    const cookieValue = Array.isArray(cookies) ? cookies[0].value : cookies;

    for (let j = 0; j < 5; j++) {
      const adPayload = {
        name: `Тестовое объявление ${j} от пользователя ${user.seller_id}`,
        description: `Это тестовое описание для объявления ${j}. Тут может быть любой текст.`,
        category: randomIntBetween(0, 100),
        images_qty: randomIntBetween(0, 2)
      };
      
      const adRes = http.post(`${BASE}/ads/`, JSON.stringify(adPayload), {
        headers: { 
          'Content-Type': 'application/json',
          'Cookie': `x-user-id=${cookieValue}`
        },
      });
      
      if (adRes.status === 201) {
        const ad = JSON.parse(adRes.body);
        console.log(`Создано объявление: ${ad.item_id} от пользователя: ${user.seller_id}`);
        ads.push({
          item_id: ad.item_id,
          seller_id: user.seller_id,
          name: ad.name,
          description: ad.description,
          category: ad.category,
          images_qty: ad.images_qty
        });
      }
    }
  }
  
  return { users, ads };
}

export default function(data) {

  const user = randomItem(data.users);

  const loginRes = http.post(`${BASE}/login`, 
    JSON.stringify({'email': user.email, 'password': user.password}), {
    headers: { 'Content-Type': 'application/json' },
  });

  if (loginRes.status !== 200) {
    console.log(`Ошибка логина пользователя ${user.seller_id}: статус ${loginRes.status}`);
    return;
  }

  const cookies = loginRes.cookies['x-user-id'];
  const cookieValue = Array.isArray(cookies) ? cookies[0].value : cookies;

  const adsListRes = http.get(`${BASE}/ads/list/${user.seller_id}`, {
    headers: { 'Cookie': `x-user-id=${cookieValue}` }
  });

  if (adsListRes.status !== 200) {
    console.log(`Ошибка получения объявлений пользователя ${user.seller_id}: статус ${adsListRes.status}`);
    return
  }

  const ads = JSON.parse(adsListRes.body)
  const active_ads = ads.filter(ad => ad.is_closed === false)
  const ad = randomItem(active_ads);
  console.log('Selected item with id: ', ad.item_id)
  
  const scenario = randomIntBetween(1, 100);
  
  
  if (scenario <= 40) {
    const simplePredictPayload = {
      item_id: ad.item_id
    };
    
    const res = http.post(`${BASE}/simple_predict/${ad.item_id}`, JSON.stringify(simplePredictPayload), {
      headers: { 'Content-Type': 'application/json' },
    });
    
    check(res, {
      'simple_predict status is 200': (r) => r.status === 200,
    });
  }
  
  else if (scenario <= 75) {
    const asyncPredictPayload = {
      item_id: ad.item_id
    };
    
    const res = http.post(`${BASE}/async_predict/${ad.item_id}`, JSON.stringify(asyncPredictPayload), {
      headers: { 'Content-Type': 'application/json' },
    });
    
    check(res, {
      'async_predict status is 200': (r) => r.status === 200,
      'async_predict returns task_id': (r) => {
        if (r.status === 200) {
          const body = JSON.parse(r.body);
          return body.task_id !== undefined;
        }
        return false;
      },
    });
  }
  
  else if (scenario <= 85) {
    const newAdPayload = {
      name: `Новое объявление ${Date.now()}`,
      description: randomString(100),
      category: randomIntBetween(0, 100),
      images_qty: randomIntBetween(0, 10)
    };
    
    const res = http.post(`${BASE}/ads/`, JSON.stringify(newAdPayload), {
      headers: { 
        'Content-Type': 'application/json',
        'Cookie': `x-user-id=${user.seller_id}`
      },
    });
    
    check(res, {
      'create ad status is 201': (r) => r.status === 201,
    });
    
    if (res.status === 201) {
      const newAd = JSON.parse(res.body);
      data.ads.push(newAd);
    }
  }
  
  else if (scenario <= 90) {
    const res = http.get(`${BASE}/ads/list/${user.seller_id}`, {
      headers: {
        'Cookie': `x-user-id=${user.seller_id}`
      }
    });
    
    check(res, {
      'get seller ads status is 200': (r) => r.status === 200,
    });
  }
  
  else if (scenario <= 93) {
    const updateRes = http.patch(`${BASE}/ads/update/${ad.item_id}?description=${encodeURIComponent('Обновленное описание ' + Date.now())}`, null, {
      headers: {
        'Cookie': `x-user-id=${user.seller_id}`
      }
    });
    
    check(updateRes, {
      'update ad status is 200': (r) => r.status === 200,
    });
  }

  
  else if (scenario <= 94) {
    const res = http.get(`${BASE}/sellers/${user.seller_id}`);
    
    check(res, {
      'get seller status is 200': (r) => r.status === 200,
    });
  }

  else {

    const asyncPredictPayload = {
      item_id: 999999
    };
    
    const res = http.post(`${BASE}/async_predict/9999999`, JSON.stringify(asyncPredictPayload), {
      headers: { 'Content-Type': 'application/json' },
    });
  }
  
  
  sleep(randomIntBetween(1, 5) / 10);
}