#
# SOFENN
# Self-Organizing Fuzzy Neural Network
#
# (sounds like soften)
#
#
# Implemented per description in
# An on-line algorithm for creating self-organizing
# fuzzy neural networks
# Leng, Prasad, McGinnity (2004)
#
#
# Andrew Edmonds - 2019
# github.com/andrewre23
#

import numpy as np
# import pandas as pd
# import matplotlib.pyplot as plt

from keras import backend as K

from sklearn.metrics import confusion_matrix, classification_report, \
    mean_absolute_error, roc_auc_score

# custom Fuzzy Layers
from .FuzzyNetwork import FuzzyNetwork


class SelfOrganizer(object):
    """
    Self-Organizing Fuzzy Neural Network
    ====================================

    Organizer
    =========

    -Implemented per description in:
        "An on-line algorithm for creating self-organizing
        fuzzy neural networks" - Leng, Prasad, McGinnity (2004)
    -Composed of 5 layers with varying "fuzzy rule" nodes

    * = samples

    Parameters
    ==========
    - X_train : np.array
        - training input data
        - shape :(train_*, features)
    - X_test  : np.array
        - testing input data
        - shape: (test_*, features)
    - y_train : np.array
        - training output data
        - shape: (train_*,)
    - y_test  : np.array
        - testing output data
        - shape: (test_*,)

    Attributes
    ==========
    - neurons : int
        - number of initial neurons
    - s_init : int
        - initial sigma for first neuron
    - epochs : int
        - training epochs
    - batch_size : int
        - training batch size
    - ifpart_thresh : float
        - threshold for if-part
    - ksig : float
        - factor to widen centers
    - max_widens : int
        - max iterations for widening centers
    - delta : float
        - threshold for error criterion whether new neuron to be added
    - prune_tol : float
        - tolerance limit for RMSE (0 < lambda < 1)
    - debug : debug flag

    Methods
    =======
    - build_model :
        - build and compile model
    - self_organize :
        - run main logic to organize FNN
    - error_criterion :
        - considers generalized performance of overall network
        - add neuron if error above predefined error threshold (delta)
    - if_part_criterion :
        - checks if current fuzzy rules cover/cluster input vector suitably
    - add_neuron :
        - add one neuron to model
    - prune_neuron :
        - remove neuron from model
    - combine_membership_functions :
        - combine similar membership functions

    Secondary Methods
    =================
    - initialize_model :
        - initialize neuron weights if only 1 neuron
    - train_model :
        - train on data
    - model_predictions :
        - yield model predictions without full evaluation
    - evaluate_model :
        - full evaluation of model on test data
    - get_layer :
        - return layer object from model by name
    - get_layer_weights :
        - get current weights from any layer in model
    - get_layer_output :
        - get test output from any layer in model
    - min_dist_vector :
        - get min_dist_vector used when adding neurons
    - new_neuron_weights :
        - get weights for new neuron to be added
    - loss_function :
        - custom loss function per Leng, Prasad, McGinnity (2004)
    """

    def __init__(self,
                 ksig=1.12, max_widens=250, err_delta=0.12,  # adding neuron or widening centers
                 prune_tol=0.85, k_mae=0.1,                  # pruning parameters
                 debug=True):

        # set debug flag
        self.__debug = debug

        # create empty network and model attributes
        self.network = None
        self.model = None

        # set self-organizing attributes
        self._ksig = ksig
        self._max_widens = max_widens
        self._delta = err_delta
        self._prune_tol = prune_tol
        self._k_mae = k_mae

        # build model and initialize if needed
        # self.model = self.build_model()
        # if self.__neurons == 1:
        #     self.__initialize_model(s_init=s_init)

    def build_network(self, X_train, X_test, y_train, y_test,  # data attributes
                      neurons=1, max_neurons=100,              # neuron initialization parameters
                      ifpart_thresh=0.1354, err_delta=0.12,    # ifpart and error thresholds
                      prob_type='classification',              # type of problem (classification/regression)
                      **kwargs):
        """
        Create FuzzyNetwork object and set network and model attributes

        Parameters
        ==========
        - X_train : training input data
            - shape :(train_*, features)
        - X_test  : testing input data
            - shape: (test_*, features)
        - y_train : training output data
            - shape: (train_*,)
        - y_test  : testing output data
            - shape: (test_*,)
        - neurons : int
            - number of initial neurons
        - max_neurons : int
            - max number of neurons
        - ifpart_thresh : float
            - threshold for if-part
        - err_delta : float
            - threshold for error criterion whether new neuron to be added
        """

        # Fuzzy network as network attribute
        self.network = FuzzyNetwork(X_train, X_test, y_train, y_test,
                                    neurons=neurons, max_neurons=max_neurons,
                                    ifpart_thresh=ifpart_thresh, err_delta=err_delta,
                                    prob_type=prob_type, debug=self.__debug, **kwargs)
        # shortcut reference to network model
        self.model = self.network.model

    def build_model(self, **kwargs):
        """
        Build and initialize Model if needed

        Layers
        ======
        1 - Input Layer
                input dataset
            - input shape  : (*, features)
        2 - Radial Basis Function Layer (Fuzzy Layer)
                layer to hold fuzzy rules for complex system
            - input : x
                shape: (*, features)
            - output : phi
                shape : (*, neurons)
        3 - Normalized Layer
                normalize each output of previous layer as
                relative amount from sum of all previous outputs
            - input : phi
                shape  : (*, neurons)
            - output : psi
                shape : (*, neurons)
        4 - Weighted Layer
                multiply bias vector (1+n_features, neurons) by
                parameter vector (1+n_features,) of parameters
                from each fuzzy rule
                multiply each product by output of each rule's
                layer from normalized layer
            - inputs : [x, psi]
                shape  : [(*, 1+features), (*, neurons)]
            - output : f
                shape : (*, neurons)
        5 - Output Layer
                summation of incoming signals from weighted layer
            - input shape  : (*, neurons)
            - output shape : (*,)
        """

        # pass parameters to network method for building model
        self.network.build_model(**kwargs)

    def compile_model(self, init_c=True, random=True, init_s=True, s_0=4.0, **kwargs):
        """
        Create and compile model
        - sets compiled model as self.model

        Parameters
        ==========
        init_c : bool
            - run method to initialize centers or take default initializations
        random : bool
            - take either random samples or first samples that appear in training data
        init_s : bool
            - run method to initialize widths or take default initializations
        s_0 : float
            - value for initial centers of neurons
        """

        # pass parameters to network method
        self.network.compile_model(init_c=init_c, random=random,
                                   init_s=init_s, s_0=s_0, **kwargs)

    def train_model(self, **kwargs):
        """
        Fit model on current training data
        """

        # pass parameters to network method
        self.network.train_model(**kwargs)

    # TODO: validate logic and update references
    def self_organize(self):
        """
        Main run function to handle organization logic

        - Train initial model in parameters then begin self-organization
        - If fails If-Part test, widen rule widths
        - If still fails, reset to original widths
            then add neuron and retrain weights
        """
        # initial training of model - yields predictions
        if self.__debug:
            print('Beginning model training...')
        self._train_model()

        # TODO: check if needed
        if self.__debug:
            print('Initial Model Evaluation')
        y_pred = self._evaluate_model(eval_thresh=self._eval_thresh)

        # create simple alias for self.network
        fuzzy_net = self.network

        # run update logic until passes criterion checks
        while not fuzzy_net.error_criterion() and not fuzzy_net.if_part_criterion():
            # run criterion checks and organize accordingly
            self.organize()

            # quit if above max neurons allowed
            if fuzzy_net.neurons >= fuzzy_net.max_neurons:
                if self.__debug:
                    print('\nMaximum neurons reached')
                    print('Terminating self-organizing process')
                    print('\nFinal Evaluation')
                    self._evaluate_model(eval_thresh=self._eval_thresh)

            # update predictions
            y_pred = self._evaluate_model(eval_thresh=self._eval_thresh)

        # print terminal message if successfully organized
        if self.__debug:
            print('\nSelf-Organization complete!')
            print('If-Part and Error Criterion satisfied')
            print('\nFinal Evaluation')
            self._evaluate_model(eval_thresh=self._eval_thresh)

    # TODO: validate logic and update references
    def organize(self):
        """
        Run one iteration of organizational logic
        - check on system error and if-part criteron
        - add neurons or prune if needed
        """

        # create simple alias for self.network
        fuzzy_net = self.network

        # get copy of initial fuzzy weights
        start_weights = fuzzy_net.get_layer_weights('FuzzyRules')

        # widen centers if necessary
        if not fuzzy_net.if_part_criterion():
            self.widen_centers()

        # add neuron if necessary
        if not fuzzy_net.error_criterion():
            # reset fuzzy weights if previously widened before adding
            curr_weights = fuzzy_net.get_layer_weights('FuzzyRules')
            if not np.array_equal(start_weights, curr_weights):
                fuzzy_net.get_layer('FuzzyRules').set_weights(start_weights)

            # add neuron and retrain model
            self.add_neuron()
            self._train_model()

        # updated prediction and prune neurons
        y_pred_new = self._model_predictions()
        self.prune_neurons(y_pred=y_pred_new)

    # TODO: validate logic and update references
    def widen_centers(self):
        """
        Widen center of neurons to better cover data
        """
        # print alert of successful widening
        if self.__debug:
            print('\nWidening centers...')

        # create simple alias for self.network
        fuzzy_net = self.network

        # get fuzzy layer and output to find max neuron output
        fuzz_layer = fuzzy_net.get_layer('FuzzyRules')

        # get old weights and create current weight vars
        c, s = fuzz_layer.get_weights()

        # repeat until if-part criterion satisfied
        # only perform for max iterations
        counter = 0
        while not fuzzy_net.if_part_criterion():

            counter += 1
            # check if max iterations exceeded
            if counter > self._max_widens:
                if self.__debug:
                    print('Max iterations reached ({})'
                          .format(counter - 1))
                return False

            # get neuron with max-output for each sample
            # then select the most common one to update
            fuzz_out = fuzzy_net.get_layer_output('FuzzyRules')
            maxes = np.argmax(fuzz_out, axis=-1)
            max_neuron = np.argmax(np.bincount(maxes.flat))

            # select minimum width to expand
            # and multiply by factor
            mf_min = s[:, max_neuron].argmin()
            s[mf_min, max_neuron] = self._ksig * s[mf_min, max_neuron]

            # update weights
            new_weights = [c, s]
            fuzz_layer.set_weights(new_weights)

        # print alert of successful widening
        if self.__debug:
            print('Centers widened after {} iterations'.format(counter))

    # TODO: validate logic and update references
    def add_neuron(self):
        """
        Add extra neuron to model while
        keeping current neuron weights
        """
        if self.__debug:
            print('\nAdding neuron...')

        # get current weights
        c_curr, s_curr = self._get_layer_weights('FuzzyRules')

        # get weights for new neuron
        ck, sk = self._new_neuron_weights()
        # expand dim for stacking
        ck = np.expand_dims(ck, axis=-1)
        sk = np.expand_dims(sk, axis=-1)
        c_new = np.hstack((c_curr, ck))
        s_new = np.hstack((s_curr, sk))

        # increase neurons and rebuild model
        # TODO: create method for building duplicate model
        self.__neurons += 1
        self.model = self.build_model()

        # update weights
        new_weights = [c_new, s_new]
        self._get_layer('FuzzyRules').set_weights(new_weights)

        # validate weights updated as expected
        final_weights = self._get_layer_weights('FuzzyRules')
        assert np.allclose(c_new, final_weights[0], 1e-3)
        assert np.allclose(s_new, final_weights[1], 1e-3)

        # retrain model since new neuron added
        self._train_model()

    # TODO: validate logic and update references
    def new_neuron_weights(self, dist_thresh=1):
        """
        Return new c and s weights for k new fuzzy neuron

        Parameters
        ==========
        dist_thresh : float
            - multiplier of average features values to use as distance thresholds

        Returns
        =======
        ck : np.array
            - average minimum distance vector across samples
            - shape: (features,)
        sk : np.array
            - average minimum distance vector across samples
            - shape: (features,)
        """
        # get input values and fuzzy weights
        x = self._X_train.values
        c, s = self._get_layer_weights('FuzzyRules')

        # get minimum distance vector
        min_dist = self._min_dist_vector()
        # get minimum distance across neurons
        # and arg-min for neuron with lowest distance
        dist_vec = min_dist.min(axis=-1)
        min_neurs = min_dist.argmin(axis=-1)

        # get min c and s weights
        c_min = c[:, min_neurs].diagonal()
        s_min = s[:, min_neurs].diagonal()
        assert c_min.shape == s_min.shape

        # set threshold distance as factor of mean
        # value for each feature across samples
        kd_i = x.mean(axis=0) * dist_thresh

        # get final weight vectors
        ck = np.where(dist_vec <= kd_i, c_min, x.mean(axis=0))
        sk = np.where(dist_vec <= kd_i, s_min, dist_vec)
        return ck, sk

    # TODO: validate logic and update references
    def min_dist_vector(self):
        """
        Get minimum distance vector

        Returns
        =======
        min_dist : np.array
            - average minimum distance vector across samples
            - shape: (features, neurons)
        """
        # get input values and fuzzy weights
        x = self._X_train.values
        samples = x.shape[0]
        c = self._get_layer_weights('FuzzyRules')[0]

        # align x and c and assert matching dims
        aligned_x = x.repeat(self.__neurons). \
            reshape(x.shape + (self.__neurons,))
        aligned_c = c.repeat(samples).reshape((samples,) + c.shape)
        assert aligned_x.shape == aligned_c.shape

        # average the minimum distance across samples
        return np.abs(aligned_x - aligned_c).mean(axis=0)

    # TODO: validate logic and update references
    def prune_neurons(self, y_pred):
        """
        Prune any unimportant neurons per effect on RMSE

        Parameters
        ==========
        y_pred : np.array
            - predicted values
        """
        if self.__debug:
            print('\nPruning neurons...')

        # quit if only 1 neuron exists
        if self.__neurons == 1:
            if self.__debug:
                print('Skipping pruning steps - only 1 neuron exists')
            return

        # calculate mean-absolute-error
        E_rmae = mean_absolute_error(self._y_test.values, y_pred)

        # create duplicate model and get both sets of model weights
        prune_model = self.build_model(False)
        # TODO: create method for building duplicate model
        act_weights = self.model.get_weights()

        # for each neuron, zero it out in prune model
        # and get change in mae for dropping neuron
        delta_E = []
        for neur in range(self.__neurons):
            # reset prune model weights to actual weights
            prune_model.set_weights(act_weights)

            # get current prune weights
            c, s, a = prune_model.get_weights()
            # zero our i neuron column in weight vector
            a[:, neur] = 0
            prune_model.set_weights([c, s, a])

            # predict values with new zeroed out weights
            neur_pred = prune_model.predict(self._X_test)
            y_pred_neur = np.squeeze(np.where(neur_pred >= self._eval_thresh, 1, 0), axis=-1)
            neur_rmae = mean_absolute_error(self._y_test.values, y_pred_neur)

            # append difference in rmse and new prediction rmse
            delta_E.append(neur_rmae - E_rmae)

        # convert delta_E to numpy array
        delta_E = np.array(delta_E)
        # choose max of tolerance or threshold limit
        E = max(self._prune_tol * E_rmae, self._k_mae)

        # iterate over each neuron in ascending importance
        # and prune until hit "important" neuron
        deleted = []
        # for each neuron up to second most important
        for neur in delta_E.argsort()[:-1]:
            # reset prune model weights to actual weights
            prune_model.set_weights(act_weights)

            # get current prune weights
            c, s, a = prune_model.get_weights()
            # zero out previous deleted neurons
            for delete in deleted:
                a[:, delete] = 0
            # zero our i neuron column in weight vector
            a[:, neur] = 0
            prune_model.set_weights([c, s, a])

            # predict values with new zeroed out weights
            neur_pred = prune_model.predict(self._X_test)
            y_pred_neur = np.squeeze(np.where(neur_pred >= self._eval_thresh, 1, 0), axis=-1)
            E_rmae_del = mean_absolute_error(self._y_test.values, y_pred_neur)

            # if E_mae_del < E
            # delete neuron
            if E_rmae_del < E:
                deleted.append(neur)
                continue
            # quit deleting if >= E
            else:
                break

        # exit if no neurons to be deleted
        if not deleted:
            if self.__debug:
                print('No neurons detected for pruning')
            return
        else:
            if self.__debug:
                print('Neurons to be deleted: ')
                print(deleted)

        # reset prune model weights to actual weights
        prune_model.set_weights(act_weights)
        # get current prune weights
        c, s, a = prune_model.get_weights()
        # delete prescribed neurons
        c = np.delete(c, deleted, axis=-1)
        s = np.delete(s, deleted, axis=-1)
        a = np.delete(a, deleted, axis=-1)

        # update neuron count and create new model with updated weights
        self.__neurons -= len(deleted)
        self.model = self.build_model(False)
        self.model.set_weights([c, s, a])

    # TODO: add function to recompile model using current settings
    # def rebuild_model(self):
    #     pass

    # TODO: create method for building duplicate model
    # def duplicate_model(self):
    #     pass

    # TODO: check if needing shorter methods for getting network layers/weights

    # TODO: add logic to demo notebook
    # def _plot_results(self, y_pred):
    #     """
    #     Plot predictions against time series
    #
    #     Parameters
    #     ==========
    #     y_pred : np.array
    #         - predicted values
    #     """
    #     # plotting results
    #     df_plot = pd.DataFrame()
    #
    #     # create pred/true time series
    #     df_plot['price'] = self._X_test['bitcoin_close']
    #     df_plot['pred'] = y_pred * df_plot['price']
    #     df_plot['true'] = self._y_test * df_plot['price']
    #     df_plot['hits'] = df_plot['price'] * (df_plot['pred'] == df_plot['true'])
    #     df_plot['miss'] = df_plot['price'] * (df_plot['pred'] != df_plot['true'])
    #
    #     fig, ax = plt.subplots(figsize=(12, 8))
    #     plt.plot(df_plot['price'], color='b')
    #     plt.bar(df_plot['price'].index, df_plot['hits'], color='g')
    #     plt.bar(df_plot['price'].index, df_plot['miss'], color='r')
    #     for label in ax.xaxis.get_ticklabels()[::400]:
    #         label.set_visible(False)
    #
    #     plt.title('BTC Close Price Against Predictions')
    #     plt.xlabel('Dates')
    #     plt.ylabel('BTC Price ($)')
    #     plt.grid(True)
    #     plt.xticks(df_plot['price'].index[::4],
    #                df_plot['price'].index[::4], rotation=70)
    #     plt.show()

    # TODO: add logic to demo notebook
    # def _evaluate_model(self, eval_thresh=0.5):
    #     """
    #     Evaluate currently trained model
    #
    #     Parameters
    #     ==========
    #     eval_thresh : float
    #         - cutoff threshold for positive/negative classes
    #
    #     Returns
    #     =======
    #     y_pred : np.array
    #         - predicted values
    #         - shape: (samples,)
    #     """
    #     # calculate accuracy scores
    #     scores = self.model.evaluate(self._X_test, self._y_test, verbose=1)
    #     raw_pred = self.model.predict(self._X_test)
    #     y_pred = np.squeeze(np.where(raw_pred >= eval_thresh, 1, 0), axis=-1)
    #
    #     # get prediction scores and prediction
    #     accuracy = scores[1]
    #     auc = roc_auc_score(self._y_test, raw_pred)
    #     mae = mean_absolute_error(self._y_test, y_pred)
    #
    #     # print accuracy and AUC score
    #     print('\nAccuracy Measures')
    #     print('=' * 21)
    #     print("Accuracy:  {:.2f}%".format(100 * accuracy))
    #     print("MAPE:      {:.2f}%".format(100 * mae))
    #     print("AUC Score: {:.2f}%".format(100 * auc))
    #
    #     # print confusion matrix
    #     print('\nConfusion Matrix')
    #     print('=' * 21)
    #     print(pd.DataFrame(confusion_matrix(self._y_test, y_pred),
    #                        index=['true:no', 'true:yes'], columns=['pred:no', 'pred:yes']))
    #
    #     # print classification report
    #     print('\nClassification Report')
    #     print('=' * 21)
    #     print(classification_report(self._y_test, y_pred, labels=[0, 1]))
    #
    #     self._plot_results(y_pred=y_pred)
    #     # return predicted values
    #     return y_pred
