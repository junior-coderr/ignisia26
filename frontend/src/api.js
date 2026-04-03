import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

export const startDemo = () => api.post('/demo')

export const uploadPDFs = (files) => {
  const fd = new FormData()
  files.forEach(f => fd.append('files', f))
  return api.post('/upload', fd)
}

export const getStatus = (examId) => api.get(`/exam/${examId}/status`)

export const getSummary = (examId) => api.get(`/exam/${examId}/summary`)

export const getClusters = (examId, qNumber) =>
  api.get(`/exam/${examId}/question/${qNumber}/clusters`)

export const applyGrade = (examId, qNumber, clusterId, score, feedback) =>
  api.post('/grade', { exam_id: examId, q_number: qNumber, cluster_id: clusterId, score, feedback })

export const exportGradesJSON = (examId) => api.get(`/exam/${examId}/export/json`)

export const exportCSVUrl = (examId) => `/api/exam/${examId}/export`

export default api
