import apiClient from '../lib/apiClient'

export const allocationService = {
  recommend: (requestId, topN = 5) =>
    apiClient
      .post('/allocation/recommend', { request_id: requestId, top_n: topN })
      .then((r) => r.data),
}
