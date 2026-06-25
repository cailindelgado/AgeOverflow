import http from 'k6/http';
import { sleep, check } from 'k6';

export const options = {
    stages: [
        { target: 1000, duration: '1m' },
        { target: 5000, duration: '5m' },
        { target: 10000, duration: '10m' },
        { target: 100000, duration: '5m' },
        { target: 1000, duration: '1m' },
        { target: 1000, duration: '1m' }
    ],
};

export default function() {
    const res = http.get('http://<put load balancer url here/api/v1/analysis');
    check(res, { 'status was 200': (r) => r.status == 200 });
    sleep(1);
}