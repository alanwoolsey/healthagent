import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
    stages: [
        {
            duration: '30s',
            target: 10
        },
        {
            duration: '3m',
            target: 10
        },
        {
            duration: '30s',
            target: 0
        }
    ],    
}

export default function () {
  const url = 'http://health-agent-alb-2068424974.us-east-2.elb.amazonaws.com/ask';

  const payload = JSON.stringify({
    message: "I would like a snapshot patient summary for patient 39254 in paragraph form limiting to no more than 100 words. I am a consulting cardiologist."
  });

  const params = {
    headers: {
      'Content-Type': 'application/json',
    },
  };

  const res = http.post(url, payload, params);

  check(res, {
    'status is 200': (r) => r.status === 200,
    'response is not empty': (r) => r.body && r.body.length > 0,
  });

  sleep(30); // wait between iterations to simulate real usage
}
