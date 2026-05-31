export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    url.hostname = 'bubabi.onrender.com';
    return fetch(new Request(url.toString(), request));
  }
};
