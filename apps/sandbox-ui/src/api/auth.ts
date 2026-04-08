import apiClient from './client'
import type { TokenResponse, LoginRequest } from '@/types'

export const authApi = {
  async login(data: LoginRequest): Promise<TokenResponse> {
    const response = await apiClient.post('/v1/auth/login', data)
    return response.data
  },

  async logout(): Promise<void> {
    await apiClient.post('/v1/auth/logout', {
      refresh_token: localStorage.getItem('refresh_token'),
    })
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  },

  async refresh(refreshToken: string): Promise<TokenResponse> {
    const response = await apiClient.post('/v1/auth/refresh', {
      refresh_token: refreshToken,
    })
    return response.data
  },
}
