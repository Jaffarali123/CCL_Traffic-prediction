# import torch
# import torch.nn as nn
# import torch.nn.functional as F
#
# from torch.distributions import Categorical
#
#
# class Memory:
#     def __init__(self, agent_num, action_dim):
#         self.agent_num = agent_num
#         self.action_dim = action_dim
#
#         self.actions = []
#         self.observations = []
#         self.pi = [[[] for _ in range(agent_num)] for _ in range(self.agent_num)]  # Store policies for each time step
#         self.reward = []
#         self.done = [[] for _ in range(agent_num)]
#
#     def get(self):
#         actions = torch.tensor(self.actions)
#         observations = self.observations
#         pi = []
#         for i in range(self.agent_num):
#             pi.append(torch.cat(self.pi[i]).view(len(self.pi[i]), self.action_dim))
#
#         reward = torch.tensor(self.reward)
#         done = self.done
#
#         return actions, observations, pi, reward, done
#
#     # def get(self):
#     #     actions = torch.tensor(self.actions)
#     #     observations = self.observations
#     #     pi = []
#     #     for i in range(self.agent_num):
#     #         pi.append(torch.cat(self.pi[i]).view(len(self.pi[i]), self.action_dim))
#     #
#     #     reward = torch.tensor(self.reward)
#     #     done = self.done
#     #
#     #     return actions, observations, pi, reward, done
#
#     def clear(self):
#         self.actions = []
#         self.observations = []
#         self.pi = [[] for _ in range(self.agent_num)]
#         self.reward = []
#         self.done = [[] for _ in range(self.agent_num)]
#
#
# class Actor(nn.Module):
#     def __init__(self, state_dim, action_dim):
#         super(Actor, self).__init__()
#
#         self.fc1 = nn.Linear(state_dim, 64)
#         self.fc2 = nn.Linear(64, 64)
#         self.fc3 = nn.Linear(64, action_dim)
#
#     def forward(self, x):
#         x = F.relu(self.fc1(x))
#         x = F.relu(self.fc2(x))
#
#         return F.softmax(self.fc3(x), dim=-1)
#
#
# class Critic(nn.Module):
#     def __init__(self, agent_num, state_dim, action_dim):
#         super(Critic, self).__init__()
#
#         input_dim = 1 + state_dim * agent_num + agent_num
#
#         self.fc1 = nn.Linear(input_dim, 64)
#         self.fc2 = nn.Linear(64, 64)
#         self.fc3 = nn.Linear(64, action_dim)
#
#     def forward(self, x):
#         x = F.relu(self.fc1(x))
#         x = F.relu(self.fc2(x))
#         return self.fc3(x)
#
#
# class COMA:
#     def __init__(self, agent_num, state_dim, action_dim, lr_c, lr_a, gamma, target_update_steps):
#         self.agent_num = agent_num
#         self.state_dim = state_dim
#         self.action_dim = action_dim
#
#         self.gamma = gamma
#         self.target_update_steps = target_update_steps
#
#         self.memory = Memory(agent_num, action_dim)
#
#         self.actors = [Actor(state_dim, action_dim) for _ in range(agent_num)]
#         self.critic = Critic(agent_num, state_dim, action_dim)
#
#         self.critic_target = Critic(agent_num, state_dim, action_dim)
#         self.critic_target.load_state_dict(self.critic.state_dict())
#
#         self.actors_optimizer = [torch.optim.Adam(self.actors[i].parameters(), lr=lr_a) for i in range(agent_num)]
#         self.critic_optimizer = torch.optim.Adam(self.critic.parameters(), lr=lr_c)
#
#         self.count = 0
#
#     def get_actions(self, observations):
#         actions = []
#         print(len(self.memory.pi))
#         for i in range(self.agent_num):
#             dist = self.actors[i](observations[i])
#             action = Categorical(dist).sample()
#
#             self.memory.pi[self.count][i].append(dist)  # Store policy for this time step
#             actions.append(action)
#
#         self.memory.observations.append(observations)
#         self.memory.actions.append(actions)
#
#         return actions
#
#     def train(self):
#         actor_optimizer = self.actors_optimizer
#         critic_optimizer = self.critic_optimizer
#
#         actions, observations, pi, reward, done = self.memory.get()
#
#
#         # print("PI: ", pi)
#
#         for i in range(self.agent_num):
#             input_critic = self.build_input_critic(i, observations, actions)
#             Q_target = self.critic_target(input_critic).detach()
#
#             action_taken = actions.type(torch.long)[:, i].reshape(-1, 1)
#
#             baseline = torch.sum(pi[i] * Q_target, dim=1).detach()
#             Q_taken_target = torch.gather(Q_target, dim=1, index=action_taken).squeeze()
#             advantage = Q_taken_target - baseline
#
#             log_pi = torch.log(torch.gather(pi[i], dim=1, index=action_taken).squeeze())
#
#             actor_loss = - torch.mean(advantage * log_pi)
#
#             actor_optimizer[i].zero_grad()
#             actor_loss.backward()
#             torch.nn.utils.clip_grad_norm_(self.actors[i].parameters(), 5)
#             actor_optimizer[i].step()
#
#             Q = self.critic(input_critic)
#
#             action_taken = actions.type(torch.long)[:, i].reshape(-1, 1)
#             Q_taken = torch.gather(Q, dim=1, index=action_taken).squeeze()
#
#             r = torch.zeros(len(reward[:, i]))
#             for t in range(len(reward[:, i])):
#                 if done[i][t]:
#                     r[t] = reward[:, i][t]
#                 else:
#                     r[t] = reward[:, i][t] + self.gamma * Q_taken_target[t + 1]
#
#             critic_loss = torch.mean((r - Q_taken) ** 2)
#
#             critic_optimizer.zero_grad()
#             critic_loss.backward()
#             torch.nn.utils.clip_grad_norm_(self.critic.parameters(), 5)
#             critic_optimizer.step()
#
#         if self.count == self.target_update_steps:
#             self.critic_target.load_state_dict(self.critic.state_dict())
#             self.count = 0
#         else:
#             self.count += 1
#
#         self.memory.clear()
#
#     def build_input_critic(self, agent_id, observations, actions):
#         batch_size = len(observations)
#
#         ids = (torch.ones(batch_size) * agent_id).view(-1, 1)
#
#         observations = torch.cat(observations).view(batch_size, self.state_dim * self.agent_num)
#         input_critic = torch.cat([observations.type(torch.float32), actions.type(torch.float32)], dim=1)
#         input_critic = torch.cat([ids, input_critic], dim=-1)
#
#         return input_critic

import torch
import torch.nn as nn
import torch.nn.functional as F

from torch.distributions import Categorical


class Memory:
    def __init__(self, agent_num, action_dim):
        self.agent_num = agent_num
        self.action_dim = action_dim

        self.actions = []
        self.observations = []
        self.pi = [[] for _ in range(agent_num)]
        self.reward = []
        self.done = [[] for _ in range(agent_num)]

    def get(self):
        actions = torch.tensor(self.actions)
        observations = self.observations
        pi = []
        for i in range(self.agent_num):
            pi.append(torch.cat(self.pi[i]).view(len(self.pi[i]), self.action_dim))

        reward = torch.tensor(self.reward)
        done = self.done

        return actions, observations, pi, reward, done

    def clear(self):
        self.actions = []
        self.observations = []
        self.pi = [[] for _ in range(self.agent_num)]
        self.reward = []
        self.done = [[] for _ in range(self.agent_num)]


import torch
import torch.nn as nn
import torch.nn.functional as F


class Actor(nn.Module):
    def __init__(self, state_dim, action_dim, hidden_size):
        super(Actor, self).__init__()

        self.lstm = nn.LSTM(state_dim,  hidden_size, batch_first=True)
        self.fc1 = nn.Linear( hidden_size, 64)
        self.fc2 = nn.Linear(64, 64)
        self.fc3 = nn.Linear(64, action_dim)

    def forward(self, x):
        # Add a batch dimension if input is 1D
        if x.dim() == 1:
            x = x.unsqueeze(0)

        # Input shape: (batch_size, sequence_length, state_dim)
        lstm_out, _ = self.lstm(x.unsqueeze(1))

        # Take the output from the last time step
        lstm_out = lstm_out[:, -1, :]

        x = F.relu(self.fc1(lstm_out))
        x = F.relu(self.fc2(x))
        x = self.fc3(x)

        return F.softmax(x, dim=-1)


# class Critic(nn.Module):
#     def __init__(self, agent_num, state_dim, action_dim, hidden_size):
#         super(Critic, self).__init__()
#
#         self.agent_num = agent_num
#         self.state_dim = state_dim
#         self.action_dim = action_dim
#         self.hidden_size = hidden_size
#
#         # Calculate input dimension considering the LSTM input
#         input_dim = 1 + state_dim * agent_num + agent_num
#
#         # Define LSTM layer
#         self.lstm = nn.LSTM(input_dim, hidden_size, batch_first=True)
#
#         # Define fully connected layers
#         self.fc1 = nn.Linear(hidden_size, 64)
#         self.fc2 = nn.Linear(64, 64)
#         self.fc3 = nn.Linear(64, action_dim)
#
#     def forward(self, x):
#         # Add a batch dimension if input is 1D
#         if x.dim() == 1:
#             x = x.unsqueeze(0)
#
#         # Input shape: (batch_size, sequence_length, input_dim)
#         lstm_out, _ = self.lstm(x.unsqueeze(1))
#
#         # Take the output from the last time step
#         lstm_out = lstm_out[:, -1, :]
#
#         # Apply fully connected layers
#         x = F.relu(self.fc1(lstm_out))
#         x = F.relu(self.fc2(x))
#         x = self.fc3(x)
#
#         return x


class Critic(nn.Module):
    def __init__(self, agent_num, state_dim, action_dim, hidden_size):
        super(Critic, self).__init__()

        input_dim = 1 + state_dim * agent_num + agent_num

        self.lstm = nn.LSTM(input_dim, hidden_size, batch_first=True)
        self.fc1 = nn.Linear(hidden_size, 64)
        self.fc2 = nn.Linear(64, 64)
        self.fc3 = nn.Linear(64, action_dim)

    def forward(self, x):
        # Input shape: (batch_size, sequence_length, input_dim)
        lstm_out, _ = self.lstm(x.unsqueeze(1))

        # Take the output from the last time step
        lstm_out = lstm_out[:, -1, :]

        x = F.relu(self.fc1(lstm_out))
        x = F.relu(self.fc2(x))
        x = self.fc3(x)

        return x




class COMA:
    def __init__(self, agent_num, state_dim, action_dim, lr_c, lr_a, gamma, target_update_steps, hidden_size=256):
        self.agent_num = agent_num
        self.state_dim = state_dim
        self.action_dim = action_dim

        self.gamma = gamma
        self.target_update_steps = target_update_steps

        self.memory = Memory(agent_num, action_dim)

        self.actors = [Actor(state_dim, action_dim, hidden_size) for _ in range(agent_num)]
        self.critic = Critic(agent_num, state_dim, action_dim, hidden_size)
        # critic_target = Critic(agent_num, state_dim, action_dim, hidden_size)

        self.critic_target = Critic(agent_num, state_dim, action_dim, hidden_size)
        self.critic_target.load_state_dict(self.critic.state_dict())

        self.actors_optimizer = [torch.optim.Adam(self.actors[i].parameters(), lr=lr_a) for i in range(agent_num)]
        self.critic_optimizer = torch.optim.Adam(self.critic.parameters(), lr=lr_c)

        self.count = 0

    def get_actions(self, observations):
        # print("Observations: ", observations)
        # observations = observations
        actions = []
        for i in range(self.agent_num):
            dist = self.actors[i](observations[i])
            action = Categorical(dist).sample()

            self.memory.pi[i].append(dist)
            actions.append(action)

        self.memory.observations.append(observations)
        self.memory.actions.append(actions)

        return actions

    def train(self):
        actor_optimizer = self.actors_optimizer
        critic_optimizer = self.critic_optimizer

        actions, observations, pi, reward, done = self.memory.get()

        print("The length of Policy vector is: ", len(pi))

        for i in range(self.agent_num):
            input_critic = self.build_input_critic(i, observations, actions)
            Q_target = self.critic_target(input_critic).detach()

            action_taken = actions.type(torch.long)[:, i].reshape(-1, 1)

            baseline = torch.sum(pi[i] * Q_target, dim=1).detach()
            Q_taken_target = torch.gather(Q_target, dim=1, index=action_taken).squeeze()
            advantage = Q_taken_target - baseline

            log_pi = torch.log(torch.gather(pi[i], dim=1, index=action_taken).squeeze())

            actor_loss = - torch.mean(advantage * log_pi)

            actor_optimizer[i].zero_grad()
            actor_loss.backward()
            torch.nn.utils.clip_grad_norm_(self.actors[i].parameters(), 5)
            actor_optimizer[i].step()

            Q = self.critic(input_critic)

            action_taken = actions.type(torch.long)[:, i].reshape(-1, 1)

            Q_taken = torch.gather(Q, dim=1, index=action_taken).squeeze()

            r = torch.zeros(len(reward[:, i]))
            # print("Value of R: ", r, len(reward[:, i]))
            # print(Q_taken_target)
            for t in range(len(reward[:, i])):
                if done[i][t]:
                    r[t] = reward[:, i]
                    # r[t] = reward[:, i][t]
                else:
                    # r[t] = reward[:, i][t] + self.gamma * Q_taken_target[t + 1]
                    r[t] = reward[:, i] + self.gamma * Q_taken_target

            critic_loss = torch.mean((r - Q_taken) ** 2)

            critic_optimizer.zero_grad()
            critic_loss.backward()
            torch.nn.utils.clip_grad_norm_(self.critic.parameters(), 5)
            critic_optimizer.step()

        if self.count == self.target_update_steps:
            self.critic_target.load_state_dict(self.critic.state_dict())
            self.count = 0
        else:
            self.count += 1

        self.memory.clear()

    def build_input_critic(self, agent_id, observations, actions):
        batch_size = len(observations)

        ids = (torch.ones(batch_size) * agent_id).view(-1, 1)

        observations = torch.cat(observations).view(batch_size, self.state_dim * self.agent_num)
        input_critic = torch.cat([observations.type(torch.float32), actions.type(torch.float32)], dim=1)
        input_critic = torch.cat([ids, input_critic], dim=-1)

        return input_critic