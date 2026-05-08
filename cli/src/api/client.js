/**
 * Creates a new analysis job in the backend.
 * @returns {{ job_id: number }}
 */
export async function createJob(filename, code, baseUrl) {
  const res = await fetch(`${baseUrl}/api/v1/jobs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ filename, code }),
  })

  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    const detail = Array.isArray(body.detail)
      ? body.detail.map(e => e.msg).join(', ')
      : body.detail ?? `HTTP ${res.status}`
    throw new Error(detail)
  }

  return res.json()
}

/**
 * Polls GET /jobs/{id} until the job is completed or failed.
 * @param {(status: string) => void} onStatusChange - callback on status transitions
 * @returns {Promise<string>} the result text
 */
export async function pollJob(jobId, baseUrl, { onStatusChange, intervalMs = 2000 } = {}) {
  let lastStatus = null

  while (true) {
    const res = await fetch(`${baseUrl}/api/v1/jobs/${jobId}`)

    if (!res.ok) throw new Error(`Failed to fetch job ${jobId}: HTTP ${res.status}`)

    const job = await res.json()

    if (job.status !== lastStatus) {
      lastStatus = job.status
      onStatusChange?.(job.status)
    }

    if (job.status === 'completed') return job.result
    if (job.status === 'failed')    throw new Error(job.error_message ?? 'Agent failed with no error message')

    await new Promise(r => setTimeout(r, intervalMs))
  }
}
