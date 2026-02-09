import apiClient from './client'
import type { TokenResponse, RegisterRequest, User } from '@/types'

export const authApi = {
  async login(email: string, password: string): Promise<TokenResponse> {
    const response = await apiClient.post('/v1/auth/login', { email, password })
    return response.data
  },

  async register(data: RegisterRequest): Promise<TokenResponse> {
    const response = await apiClient.post('/v1/auth/register', data)
    return response.data
  },

  async refresh(refreshToken: string): Promise<TokenResponse> {
    const response = await apiClient.post('/v1/auth/refresh', { refresh_token: refreshToken })
    return response.data
  },

  async logout(): Promise<void> {
    await apiClient.post('/v1/auth/logout')
  },

  async getMe(): Promise<User> {
    const response = await apiClient.get('/v1/users/me')
    return response.data
  },
}
